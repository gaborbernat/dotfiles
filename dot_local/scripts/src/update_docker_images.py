# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
"""Update local Docker images that came from a registry to their latest digest.

A single `docker images --digests` call lists the images; a single
`docker image inspect` (by image id, which always resolves — inspecting by tag
intermittently reports "no such object") classifies them. Images with no
RepoDigests are locally built: they are never looked up in a registry, only the
stale ones are pruned. For registry images the remote digest comes from
`crane digest` (daemon-free, reuses the docker login credentials, so Docker Hub,
GHCR, and Artifactory OCI all work); only images whose digest differs are
pulled. Rows are ordered newest-built first, and dangling data is pruned at the
end. Progress renders live as each image resolves.
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
_OLDEST: Final[datetime] = datetime.min.replace(tzinfo=UTC)
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
    cutoff: datetime = datetime.now(UTC) - _STALE_LOCAL_AGE
    registry: list[ImageStatus] = []
    stale_local: list[str] = []
    for image, image_id, digest, size in rows:
        repo_digests, created = inspected.get(image_id, (None, None))
        if repo_digests is None:
            continue
        if matched := digests_for_repo(image.rsplit(":", 1)[0], repo_digests):
            registry.append(ImageStatus(image, digest if digest.startswith("sha256:") else "", size, created, matched))
        elif created is not None and created < cutoff:
            stale_local.append(image)
    registry.sort(key=lambda status: status.created or _OLDEST, reverse=True)
    return registry, stale_local


def bulk_inspect(image_ids: list[str]) -> dict[str, tuple[set[str], datetime | None]]:
    if not image_ids:
        return {}
    result: subprocess.CompletedProcess[str] = subprocess.run(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{.Id}}\t{{json .RepoDigests}}\t{{.Created}}",
            *sorted(set(image_ids)),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    inspected: dict[str, tuple[set[str], datetime | None]] = {}
    for line in result.stdout.splitlines():
        image_id, _, rest = line.partition("\t")
        digests_json, _, created = rest.partition("\t")
        inspected[image_id] = (set(json.loads(digests_json or "[]")), parse_created(created))
    return inspected


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
    finish(status, lock, "updated" if ok else "failed", started, "" if ok else error)


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
    table.add_column("Updated", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Time", justify="right")
    with lock:
        rows = [(s.image, s.state, s.detail, s.created, s.size, s.duration) for s in images]
    for index, (image, state, detail, created, size, duration) in enumerate(rows, 1):
        label: str = f"{state} [dim]({detail})[/dim]" if detail else state
        styled: str = f"[{_STATE_STYLE.get(state, '')}]{label}[/]"
        table.add_row(str(index), image, styled, format_age(created), size, format_duration(duration))
    return table


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
    created: datetime | None
    registry_digests: set[str] = field(default_factory=set)
    state: str = "checking"
    detail: str = ""
    duration: float | None = None


if __name__ == "__main__":
    main()
