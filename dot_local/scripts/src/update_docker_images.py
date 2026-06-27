# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
"""Update local Docker images that came from a registry to their latest digest.

The image list, digest, and size come from a single `docker images --digests`
call. Locally built images (empty RepoDigests, no registry source) are not
checked; the stale ones are removed afterwards. For registry images the remote
digest comes from `crane digest` (daemon-free, reuses the docker login
credentials, so Docker Hub, GHCR, and Artifactory OCI all work); only images
whose digest differs are pulled. The status column carries the failure reason
and each row shows how long it took. Finally dangling data is pruned. Progress
renders live as each image resolves.
"""

from __future__ import annotations

import json
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
_STALE_LOCAL_AGE: Final[timedelta] = timedelta(days=7)
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
        ["docker", "images", "--digests", "--format", "{{.Repository}}:{{.Tag}}\t{{.Digest}}\t{{.Size}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    candidates: list[ImageStatus] = []
    for raw_line in listing.stdout.splitlines():
        if len(parts := raw_line.split("\t")) != 3 or "<none>" in parts[0]:
            continue
        candidates.append(ImageStatus(parts[0], parts[1] if parts[1].startswith("sha256:") else "", parts[2]))

    with ThreadPoolExecutor() as executor:
        details = list(executor.map(inspect_image, [candidate.image for candidate in candidates]))
    cutoff: datetime = datetime.now(UTC) - _STALE_LOCAL_AGE
    registry: list[ImageStatus] = []
    stale_local: list[str] = []
    for status, (digests, created) in zip(candidates, details, strict=True):
        if digests is None:
            registry.append(status)  # inspect flaked; let crane decide rather than drop it
        elif digests:
            status.registry_digests = digests
            registry.append(status)
        elif created is not None and created < cutoff:
            stale_local.append(status.image)
    registry.sort(key=lambda status: status.image)
    return registry, stale_local


def inspect_image(image: str) -> tuple[set[str] | None, datetime | None]:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}\t{{.Created}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None, None
    repo_digests_json, _, created = result.stdout.strip().partition("\t")
    repo: str = image.rsplit(":", 1)[0]
    digests: set[str] = set()
    for entry in json.loads(repo_digests_json or "[]"):
        name, _, digest = entry.partition("@")
        if name == repo and digest:
            digests.add(digest)
    return digests, parse_created(created)


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
        futures = [executor.submit(process_image, status, lock) for status in images]
        while any(not future.done() for future in futures):
            live.update(render(images, lock))
            time.sleep(0.1)
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
    ok, error = docker_pull(status.image)
    if not ok:
        finish(status, lock, "failed", started, error)
        return
    with lock:
        status.local = current_digest(status.image) or remote
    finish(status, lock, "updated", started)


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
    error: str = result.stderr.lower()
    if any(token in error for token in ("unauthorized", "401", "denied", "403", "forbidden")):
        return None, "auth required"
    return None, short_error(result.stderr)


def short_error(text: str, limit: int = 44) -> str:
    return next((stripped for raw in reversed(text.splitlines()) if (stripped := raw.strip())), "")[:limit]


def docker_pull(image: str) -> tuple[bool, str]:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "pull", image], check=False, capture_output=True, text=True
    )
    return (True, "") if result.returncode == 0 else (False, short_error(result.stderr))


def current_digest(image: str) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--digests", "--format", "{{.Digest}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return lines[0].strip() if (lines := result.stdout.splitlines()) else ""


def finish(status: ImageStatus, lock: threading.Lock, state: str, started: float, detail: str = "") -> None:
    with lock:
        status.state = state
        status.detail = detail
        status.duration = time.monotonic() - started


def render(images: list[ImageStatus], lock: threading.Lock) -> Table:
    table: Table = Table(title="Docker Image Update Summary", box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right")
    table.add_column("Image", style="bold")
    table.add_column("Status")
    table.add_column("Digest", overflow="fold")
    table.add_column("Size", justify="right")
    table.add_column("Time", justify="right")
    with lock:
        rows = [(s.image, s.state, s.detail, s.local.removeprefix("sha256:"), s.size, s.duration) for s in images]
    sha_len: int = find_unique_sha_length([row[3] for row in rows])
    for index, (image, state, detail, digest, size, duration) in enumerate(rows, 1):
        label: str = f"{state} [dim]({detail})[/dim]" if detail else state
        styled: str = f"[{_STATE_STYLE.get(state, '')}]{label}[/]"
        table.add_row(str(index), image, styled, digest[:sha_len], size, format_duration(duration))
    return table


def format_duration(duration: float | None) -> str:
    if duration is None:
        return ""
    if duration < 60:
        return f"{duration:.1f}s"
    return f"{int(duration // 60)}m{int(duration % 60)}s"


def find_unique_sha_length(shas: list[str], min_len: int = 10) -> int:
    present: list[str] = list({sha for sha in shas if sha})
    for length in range(min_len, 65):
        if len({sha[:length] for sha in present}) == len(present):
            return length
    return 64


def cleanup_local(images: list[str]) -> None:
    # Docker exposes no last-used timestamp, so "unused" is approximated by build age
    # plus `docker rmi` refusing to remove an image a container still references.
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
    registry_digests: set[str] = field(default_factory=set)
    state: str = "checking"
    detail: str = ""
    duration: float | None = None


if __name__ == "__main__":
    main()
