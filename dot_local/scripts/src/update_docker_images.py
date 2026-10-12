# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=15.0.0",
# ]
# ///
"""Update images pulled from a registry without removing local Docker data."""

from __future__ import annotations

import json
import os
import platform
import pty
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Final

from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table

_CONSOLE: Final[Console] = Console()
_OLDEST: Final[datetime] = datetime.min.replace(tzinfo=UTC)
_HOST_ARCH: Final[str] = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())
_DOWNLOAD_RE: Final[re.Pattern[str]] = re.compile(
    r"([0-9a-f]{6,}): Downloading\s+\[[^\]]*\]\s+[0-9.]+[A-Za-z]+/([0-9.]+[A-Za-z]+)"
)
_SIZE_UNITS: Final[dict[str, int]] = {"b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4}
_STATE_STYLE: Final[dict[str, str]] = {
    "checking": "dim",
    "pulling": "yellow",
    "up to date": "blue",
    "updated": "green",
    "unreachable": "yellow",
    "failed": "red",
    "error": "red",
}


def main() -> None:
    registry = scan_images()
    if registry:
        update_registry_images(registry)
    else:
        _CONSOLE.print("No registry-backed images to check.")
    if any(image.state in {"unreachable", "failed", "error"} for image in registry):
        raise SystemExit(1)


def scan_images() -> list[ImageStatus]:
    listing: subprocess.CompletedProcess[str] = subprocess.run(
        [
            "docker",
            "images",
            "--digests",
            "--no-trunc",
            "--format",
            "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Digest}}\t{{.Size}}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if listing.returncode:
        msg = f"docker images failed: {short_error(listing.stderr)}"
        raise RuntimeError(msg)
    rows: list[list[str]] = [
        parts
        for raw_line in listing.stdout.splitlines()
        if len(parts := raw_line.split("\t")) == 4 and "<none>" not in parts[0]
    ]
    inspected = bulk_inspect([row[1] for row in rows])
    registry: list[ImageStatus] = []
    for image, image_id, digest, size in rows:
        if (info := inspected.get(image_id)) is None:
            continue
        repo_digests, created, image_platform, pulled_from = info
        repo = image.rsplit(":", 1)[0]
        # The containerd store gives local builds a RepoDigest of their own name, so only Identity.Pull
        # tells a registry pull apart from a build, load, or local tag.
        if canonical_repo(repo) in pulled_from and (matched := digests_for_repo(repo, repo_digests)):
            registry.append(
                ImageStatus(
                    image=image,
                    local=digest if digest.startswith("sha256:") else "",
                    size=size,
                    created=created,
                    platform=image_platform,
                    registry_digests=matched,
                )
            )
    registry.sort(key=lambda status: status.created or _OLDEST, reverse=True)
    return registry


def bulk_inspect(image_ids: list[str]) -> dict[str, tuple[set[str], datetime | None, str, set[str]]]:
    if not image_ids:
        return {}
    # Raw JSON rather than --format: Docker omits Identity for images it has no record for, and a
    # template referencing a missing key aborts the whole batch.
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "image", "inspect", *sorted(set(image_ids))],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        msg = f"docker image inspect failed: {short_error(result.stderr)}"
        raise RuntimeError(msg)
    entries: list[dict[str, Any]] = json.loads(result.stdout)
    return {
        entry["Id"]: (
            set(entry.get("RepoDigests") or []),
            parse_created(entry.get("Created", "")),
            f"{entry.get('Os', '')}/{entry.get('Architecture', '')}",
            {pull["Repository"] for pull in (entry.get("Identity") or {}).get("Pull") or []},
        )
        for entry in entries
    }


def canonical_repo(repo: str) -> str:
    if has_registry_host(repo):
        return repo
    return f"docker.io/{repo}" if "/" in repo else f"docker.io/library/{repo}"


def has_registry_host(repo: str) -> bool:
    host, slash, _ = repo.partition("/")
    return bool(slash) and (host == "localhost" or "." in host or ":" in host)


def digests_for_repo(repo: str, entries: set[str]) -> set[str]:
    matched: set[str] = set()
    for entry in entries:
        name, _, digest = entry.partition("@")
        if name == repo and digest:
            matched.add(digest)
    return matched


def parse_created(value: str) -> datetime | None:
    if not (text := value.strip()):
        return None
    try:
        return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", text.replace("Z", "+00:00")))
    except ValueError:
        return None


def update_registry_images(images: list[ImageStatus]) -> None:
    lock = threading.Lock()
    with (
        Live(render(images, lock), console=_CONSOLE, refresh_per_second=12, transient=True) as live,
        ThreadPoolExecutor() as executor,
    ):
        futures = {executor.submit(process_image, status, lock): status for status in images}
        while any(not future.done() for future in futures):
            live.update(render(images, lock))
            time.sleep(0.1)
    # Surface worker exceptions instead of leaving the image stuck at "checking" with no error.
    for future, status in futures.items():
        try:
            future.result()
        except Exception as exc:  # noqa: BLE001
            with lock:
                status.state = "error"
                status.detail = str(exc)
    _CONSOLE.print(render(images, lock))


def process_image(status: ImageStatus, lock: threading.Lock) -> None:
    started: float = time.monotonic()
    remote, reason = registry_digest(status.image)
    if remote is None:
        finish(status, lock, "unreachable", started, reason)
        return
    if remote == status.local or remote in status.registry_digests:
        finish(status, lock, "up to date", started)
        return
    with lock:
        status.state = "pulling"
    ok, error, downloaded = docker_pull(status.image)
    if not ok:
        finish(status, lock, "failed", started, error)
        return
    finish(
        status, lock, "updated", started, update_detail(status.local, remote, downloaded, time.monotonic() - started)
    )


def registry_digest(image: str) -> tuple[str | None, str]:
    if shutil.which("crane"):
        command = ["crane", "digest", image]
    elif shutil.which("skopeo"):
        command = ["skopeo", "inspect", "--format", "{{.Digest}}", f"docker://{image}"]
    else:
        return None, "crane or skopeo not installed"
    result: subprocess.CompletedProcess[str] = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and (digest := result.stdout.strip()):
        return digest, ""
    if any(token in result.stderr.lower() for token in ("unauthorized", "401", "denied", "403", "forbidden")):
        return None, "auth required"
    return None, short_error(result.stderr)


def short_error(text: str, limit: int = 44) -> str:
    return next((stripped for raw in reversed(text.splitlines()) if (stripped := raw.strip())), "")[:limit]


def docker_pull(image: str) -> tuple[bool, str, int]:
    # A pty makes docker emit per-layer progress ("Downloading [..] done/total"); summing each
    # layer's total yields the bytes actually fetched, which the non-tty capture_output never prints.
    layer_totals: dict[str, int] = {}
    output: list[str] = []
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execvp("docker", ["docker", "pull", image])
        except OSError:
            os._exit(127)
    try:
        while True:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            if not data:
                break
            text = data.decode("utf-8", "replace")
            output.append(text)
            for layer, total in _DOWNLOAD_RE.findall(text):
                layer_totals[layer] = parse_size(total)
    finally:
        os.close(fd)
    if os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1]) == 0:
        return True, "", sum(layer_totals.values())
    return False, short_error("".join(output)), 0


def parse_size(text: str) -> int:
    if match := re.match(r"\s*([0-9.]+)\s*([A-Za-z]+)", text):
        return int(float(match.group(1)) * _SIZE_UNITS.get(match.group(2).lower(), 1))
    return 0


def update_detail(old: str, new: str, downloaded: int, duration: float) -> str:
    move: str = f"{short_digest(old)} → {short_digest(new)}"
    if downloaded and duration:
        return f"{move} · {format_bytes(downloaded)} @ {format_bytes(downloaded / duration)}/s"
    return move


def short_digest(digest: str) -> str:
    return digest.removeprefix("sha256:")[:12] if digest else "?"


def format_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1000:
            return f"{num:.0f}{unit}" if unit == "B" else f"{num:.1f}{unit}"
        num /= 1000
    return f"{num:.1f}TB"


def finish(status: ImageStatus, lock: threading.Lock, state: str, started: float, detail: str = "") -> None:
    with lock:
        status.state = state
        status.detail = detail
        status.duration = time.monotonic() - started


def render(images: list[ImageStatus], lock: threading.Lock) -> Table:
    table: Table = Table(title="Docker Image Update Summary", box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right")
    table.add_column("Image", style="bold")
    table.add_column("Platform")
    table.add_column("Status")
    table.add_column("Updated", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Time", justify="right")
    with lock:
        rows = [(s.image, s.platform, s.state, s.detail, s.created, s.size, s.duration) for s in images]
    for index, (image, image_platform, state, detail, created, size, duration) in enumerate(rows, 1):
        styled: str = f"[{_STATE_STYLE.get(state, '')}]{state}{f' [dim]({detail})[/dim]' if detail else ''}[/]"
        table.add_row(
            str(index),
            image,
            render_platform(image_platform),
            styled,
            format_age(created),
            size,
            format_duration(duration),
        )
    return table


def render_platform(image_platform: str) -> str:
    # Flag a mismatch (e.g. an amd64 image pulled onto an arm64 host) so emulated images stand out.
    arch: str = image_platform.split("/")[1] if "/" in image_platform else ""
    if arch and arch != _HOST_ARCH:
        return f"[yellow]{image_platform}[/]"
    return image_platform


def format_age(created: datetime | None) -> str:
    if created is None:
        return ""
    days: int = (datetime.now(UTC) - created).days
    if days < 1:
        return "today"
    if days < 7:
        return f"{days}d ago"
    if days < 30:
        return f"{days // 7}w ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def format_duration(duration: float | None) -> str:
    if duration is None:
        return ""
    if duration < 60:
        return f"{duration:.1f}s"
    return f"{int(duration // 60)}m{int(duration % 60)}s"


@dataclass
class ImageStatus:
    image: str
    local: str
    size: str
    created: datetime | None
    platform: str = ""
    registry_digests: set[str] = field(default_factory=set)
    state: str = "checking"
    detail: str = ""
    duration: float | None = None


if __name__ == "__main__":
    main()
