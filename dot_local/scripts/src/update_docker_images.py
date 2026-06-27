# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
"""Update local Docker images to the latest digest published in their registry.

The local image list, digest, and size come from a single `docker images
--digests` call (robust: a follow-up `docker inspect` can intermittently report
"no such object" for a tag that `docker images` lists). The remote digest comes
from `crane digest`, which is daemon-free and reuses the existing docker login
credentials, so it works against Docker Hub, GHCR, and Artifactory OCI. Only
images whose registry digest differs are pulled, so an already-current run does
zero pulls. When crane cannot resolve an image, it falls back to `docker pull`.
Progress renders live as each image resolves.
"""

from __future__ import annotations

import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

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
    "failed": "red",
}


@dataclass
class ImageStatus:
    image: str
    local: str
    size: str
    state: str = "checking"
    remote: str = ""


def main() -> None:
    images: list[ImageStatus] = get_images()
    if not images:
        console.print("No registry-backed images to check.")
        return
    lock = threading.Lock()
    with Live(render(images, lock), console=console, refresh_per_second=12) as live:
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_image, status, lock) for status in images]
            while any(not future.done() for future in futures):
                live.update(render(images, lock))
                time.sleep(0.1)
        live.update(render(images, lock))


def get_images() -> list[ImageStatus]:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--digests", "--format", "{{.Repository}}:{{.Tag}}\t{{.Digest}}\t{{.Size}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    images: list[ImageStatus] = []
    for raw_line in result.stdout.splitlines():
        parts: list[str] = raw_line.split("\t")
        if len(parts) != 3:
            continue
        image, digest, size = parts
        if "<none>" in image or not digest.startswith("sha256:"):
            continue
        images.append(ImageStatus(image=image, local=digest, size=size))
    images.sort(key=lambda status: status.image)
    return images


def process_image(status: ImageStatus, lock: threading.Lock) -> None:
    remote: str | None = crane_digest(status.image)
    with lock:
        status.remote = remote or ""
    if remote is not None and remote == status.local:
        with lock:
            status.state = "up to date"
        return
    with lock:
        status.state = "pulling"
    old: str = status.local
    if not docker_pull(status.image):
        with lock:
            status.state = "failed"
        return
    new: str = current_digest(status.image) or remote or old
    with lock:
        status.local = new
        status.state = "updated" if new != old else "up to date"


def crane_digest(image: str) -> str | None:
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            ["crane", "digest", image],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    return digest if result.returncode == 0 and (digest := result.stdout.strip()) else None


def current_digest(image: str) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--digests", "--format", "{{.Digest}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    lines: list[str] = result.stdout.splitlines()
    return lines[0].strip() if lines else ""


def docker_pull(image: str) -> bool:
    return subprocess.run(["docker", "pull", image], check=False, capture_output=True, text=True).returncode == 0


def render(images: list[ImageStatus], lock: threading.Lock) -> Table:
    table: Table = Table(title="Docker Image Update Summary", box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right")
    table.add_column("Image", style="bold")
    table.add_column("Status")
    table.add_column("Local", overflow="fold")
    table.add_column("Remote", overflow="fold")
    table.add_column("Size", justify="right")
    with lock:
        rows: list[tuple[str, str, str, str, str]] = [
            (s.image, s.state, s.local.removeprefix("sha256:"), s.remote.removeprefix("sha256:"), s.size)
            for s in images
        ]
    sha_len: int = find_unique_sha_length([row[2] for row in rows] + [row[3] for row in rows])
    for index, (image, state, local, remote, size) in enumerate(rows, 1):
        style: str = _STATE_STYLE.get(state, "")
        table.add_row(str(index), image, f"[{style}]{state}[/{style}]", local[:sha_len], remote[:sha_len], size)
    return table


def find_unique_sha_length(shas: list[str], min_len: int = 10) -> int:
    present: list[str] = list({sha for sha in shas if sha})
    for length in range(min_len, 65):
        if len({sha[:length] for sha in present}) == len(present):
            return length
    return 64


if __name__ == "__main__":
    main()
