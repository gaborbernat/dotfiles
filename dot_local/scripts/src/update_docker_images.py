# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
"""Update local Docker images that came from a registry to their latest digest.

The image list, digest, and size come from a single `docker images --digests`
call. Locally built images (empty RepoDigests, no registry source) are filtered
out up front. For the rest, the remote digest comes from `crane digest`
(daemon-free, reuses the docker login credentials, so Docker Hub, GHCR, and
Artifactory OCI all work); only images whose digest differs are pulled. The
status column carries the failure reason, and each row shows how long it took.
Progress renders live as each image resolves.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table

console = Console()

_STATE_STYLE: dict[str, str] = {
    "checking": "dim",
    "pulling": "yellow",
    "up to date": "blue",
    "updated": "green",
    "unreachable": "yellow",
    "failed": "red",
}


@dataclass
class ImageStatus:
    image: str
    local: str
    size: str
    registry_digests: set[str] = field(default_factory=set)
    state: str = "checking"
    detail: str = ""
    duration: float | None = None


def main() -> None:
    images: list[ImageStatus] = get_images()
    if not images:
        console.print("No registry-backed images to check.")
        return
    lock = threading.Lock()
    with (
        Live(render(images, lock), console=console, refresh_per_second=12, transient=True) as live,
        ThreadPoolExecutor() as executor,
    ):
        futures = [executor.submit(process_image, status, lock) for status in images]
        while any(not future.done() for future in futures):
            live.update(render(images, lock))
            time.sleep(0.1)
    console.print(render(images, lock))


def get_images() -> list[ImageStatus]:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--digests", "--format", "{{.Repository}}:{{.Tag}}\t{{.Digest}}\t{{.Size}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    candidates: list[ImageStatus] = []
    for raw_line in result.stdout.splitlines():
        parts: list[str] = raw_line.split("\t")
        if len(parts) != 3:
            continue
        image, digest, size = parts
        if "<none>" in image:
            continue
        candidates.append(ImageStatus(image=image, local=digest if digest.startswith("sha256:") else "", size=size))

    with ThreadPoolExecutor() as executor:
        digest_sets: list[set[str] | None] = list(
            executor.map(repo_digests, [candidate.image for candidate in candidates])
        )
    images: list[ImageStatus] = []
    for status, digests in zip(candidates, digest_sets, strict=True):
        if digests is not None and not digests:
            continue
        status.registry_digests = digests or set()
        images.append(status)
    images.sort(key=lambda status: status.image)
    return images


def repo_digests(image: str) -> set[str] | None:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    repo: str = image.rsplit(":", 1)[0]
    digests: set[str] = set()
    for entry in json.loads(result.stdout or "[]"):
        name, _, digest = entry.partition("@")
        if name == repo and digest:
            digests.add(digest)
    return digests


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


def finish(status: ImageStatus, lock: threading.Lock, state: str, started: float, detail: str = "") -> None:
    with lock:
        status.state = state
        status.detail = detail
        status.duration = time.monotonic() - started


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


def current_digest(image: str) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--digests", "--format", "{{.Digest}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    lines: list[str] = result.stdout.splitlines()
    return lines[0].strip() if lines else ""


def docker_pull(image: str) -> tuple[bool, str]:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "pull", image], check=False, capture_output=True, text=True
    )
    return (True, "") if result.returncode == 0 else (False, short_error(result.stderr))


def short_error(text: str, limit: int = 44) -> str:
    line: str = next((stripped for raw in reversed(text.splitlines()) if (stripped := raw.strip())), "")
    return line[:limit]


def render(images: list[ImageStatus], lock: threading.Lock) -> Table:
    table: Table = Table(title="Docker Image Update Summary", box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right")
    table.add_column("Image", style="bold")
    table.add_column("Status")
    table.add_column("Digest", overflow="fold")
    table.add_column("Size", justify="right")
    table.add_column("Time", justify="right")
    with lock:
        rows: list[tuple[str, str, str, str, str, float | None]] = [
            (s.image, s.state, s.detail, s.local.removeprefix("sha256:"), s.size, s.duration) for s in images
        ]
    sha_len: int = find_unique_sha_length([row[3] for row in rows])
    for index, (image, state, detail, digest, size, duration) in enumerate(rows, 1):
        style: str = _STATE_STYLE.get(state, "")
        label: str = f"{state} [dim]({detail})[/dim]" if detail else state
        table.add_row(
            str(index), image, f"[{style}]{label}[/{style}]", digest[:sha_len], size, format_duration(duration)
        )
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


if __name__ == "__main__":
    main()
