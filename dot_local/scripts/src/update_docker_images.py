# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
"""Update registry-sourced Docker images to their latest digest; prune dormant local ones.

Classification is by reference: an image whose repo carries a registry host (the part
before the first "/" contains "." or ":", or is localhost) is registry-backed; anything
else is a local build, including ones carrying a hostless RepoDigest from a mirror push.
Inspection is keyed by image id, which always resolves — inspecting by tag intermittently
reports "no such object". Registry images are always kept and refreshed via `crane digest`
(daemon-free, reuses docker credentials); only those whose digest moved are pulled. Local
images are pruned only once dormant for two weeks — by container last-run time, falling back
to build time when no run was recorded. The table flags a platform differing from the host arch.
"""

from __future__ import annotations

import json
import os
import platform
import pty
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final

from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table

_CONSOLE: Final[Console] = Console()
_STALE_LOCAL_AGE: Final[timedelta] = timedelta(days=14)
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
}


def main() -> None:
    registry, stale_local = scan_images()
    if registry:
        update_registry_images(registry)
    else:
        _CONSOLE.print("No registry-backed images to check.")
    cleanup_local(stale_local)
    prune_system()


def scan_images() -> tuple[list[ImageStatus], list[str]]:
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
    rows: list[list[str]] = [
        parts
        for raw_line in listing.stdout.splitlines()
        if len(parts := raw_line.split("\t")) == 4 and "<none>" not in parts[0]
    ]
    inspected = bulk_inspect([row[1] for row in rows])
    runs = last_run_times()
    cutoff: datetime = datetime.now(UTC) - _STALE_LOCAL_AGE
    registry: list[ImageStatus] = []
    stale_local: list[str] = []
    for image, image_id, digest, size in rows:
        repo_digests, created, image_platform = inspected.get(image_id, (None, None, ""))
        if repo_digests is None:
            continue
        repo = image.rsplit(":", 1)[0]
        if has_registry_host(repo) and (matched := digests_for_repo(repo, repo_digests)):
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
        elif (last_active := runs.get(image_id, created)) is not None and last_active < cutoff:
            stale_local.append(image)
    registry.sort(key=lambda status: status.created or _OLDEST, reverse=True)
    return registry, stale_local


def bulk_inspect(image_ids: list[str]) -> dict[str, tuple[set[str], datetime | None, str]]:
    if not image_ids:
        return {}
    result: subprocess.CompletedProcess[str] = subprocess.run(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{.Id}}\t{{json .RepoDigests}}\t{{.Created}}\t{{.Os}}/{{.Architecture}}",
            *sorted(set(image_ids)),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    inspected: dict[str, tuple[set[str], datetime | None, str]] = {}
    for line in result.stdout.splitlines():
        image_id, _, rest = line.partition("\t")
        digests_json, _, rest = rest.partition("\t")
        created, _, image_platform = rest.partition("\t")
        # {{json .RepoDigests}} emits "null" for a nil slice, which json.loads -> None; coerce to empty.
        digests = json.loads(digests_json) if digests_json.strip() else []
        inspected[image_id] = (set(digests or []), parse_created(created), image_platform)
    return inspected


def last_run_times() -> dict[str, datetime]:
    # The only signal for when an image was last run is a container's State.StartedAt; with ephemeral
    # (--rm) containers none survive, so scan_images falls back to the image build time.
    container_ids: list[str] = subprocess.run(
        ["docker", "ps", "-a", "--no-trunc", "--format", "{{.ID}}"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.split()
    if not container_ids:
        return {}
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "container", "inspect", "--format", "{{.Image}}\t{{.State.StartedAt}}", *container_ids],
        check=False,
        capture_output=True,
        text=True,
    )
    runs: dict[str, datetime] = {}
    for line in result.stdout.splitlines():
        image_id, _, started = line.partition("\t")
        # Docker's zero time marks a container that was created but never started
        if started.startswith("0001"):
            continue
        if (when := parse_created(started)) and when > runs.get(image_id, _OLDEST):
            runs[image_id] = when
    return runs


def has_registry_host(repo: str) -> bool:
    # Docker treats the part before the first "/" as a registry host only when it looks like one
    # (contains "." or ":", or is "localhost"); otherwise the ref defaults to docker.io, so a local
    # build like "guild-week-website-app" or "linterator-cli-cache/x" must not be sent to a registry.
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
    remote, reason = crane_digest(status.image)
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


def crane_digest(image: str) -> tuple[str | None, str]:
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            ["crane", "digest", image],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None, "crane not installed"
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


def cleanup_local(images: list[str]) -> None:
    # Staleness is decided in scan_images (last run, else build time); `docker rmi` still
    # refuses to remove an image a container references, a final safety net.
    if not (removed := [image for image in images if remove_image(image)]):
        return
    _CONSOLE.print(f"[bright_black]Removed {len(removed)} stale local image(s) (no registry source):[/]")
    for image in removed:
        _CONSOLE.print(f"[bright_black]  {image}[/]")


def remove_image(image: str) -> bool:
    return subprocess.run(["docker", "rmi", image], check=False, capture_output=True, text=True).returncode == 0


def prune_system() -> None:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "system", "prune", "-f", "--volumes"], check=False, capture_output=True, text=True
    )
    summary: str = next((line.strip() for line in result.stdout.splitlines() if "reclaimed" in line.lower()), "")
    _CONSOLE.print(f"[bright_black]{summary or 'Pruned dangling docker data.'}[/]")


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
