# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
"""Update local Docker images to the latest digest published in their registry.

Detection uses `crane digest`, which is daemon-free and reads the existing
docker login credentials, so it works against Docker Hub, GHCR, and Artifactory
OCI endpoints alike. Only images whose registry digest differs from the local
one are pulled, so an already-current run does zero pulls. When crane cannot
resolve an image (auth, network, non-OCI registry) it falls back to `docker
pull`, which is authoritative. Progress renders live as each image resolves.
"""

from __future__ import annotations

import json
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
    state: str = "checking"
    local: str = ""
    remote: str = ""
    size: str = ""


def main() -> None:
    images: list[ImageStatus] = sorted((ImageStatus(image) for image in get_images()), key=lambda s: s.image)
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


def get_images() -> list[str]:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    return [
        line
        for raw_line in result.stdout.splitlines()
        if (line := raw_line.strip()) and "<none>" not in line and has_repo_digests(line)
    ]


def has_repo_digests(image: str) -> bool:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "inspect", "--format", "{{.RepoDigests}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() not in ("[]", "")


def process_image(status: ImageStatus, lock: threading.Lock) -> None:
    image: str = status.image
    local_digests: set[str] = repo_digests(image)
    remote: str | None = crane_digest(image)
    with lock:
        status.size = get_image_size(image)
        status.local = next(iter(local_digests), "").removeprefix("sha256:")
        status.remote = (remote or "").removeprefix("sha256:")
    if remote is not None and remote in local_digests:
        with lock:
            status.state = "up to date"
        return
    with lock:
        status.state = "pulling"
    old_id: str = image_id(image)
    if not docker_pull(image):
        with lock:
            status.state = "failed"
        return
    with lock:
        status.local = next(iter(repo_digests(image)), "").removeprefix("sha256:") or status.local
        status.state = "updated" if image_id(image) != old_id else "up to date"


def repo_digests(image: str) -> set[str]:
    repo: str = image.rsplit(":", 1)[0]
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "inspect", "--format", "{{json .RepoDigests}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return set()
    digests: set[str] = set()
    for entry in json.loads(result.stdout or "[]"):
        name, _, digest = entry.partition("@")
        if name == repo and digest:
            digests.add(digest)
    return digests


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


def image_id(image: str) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--no-trunc", "--format", "{{.ID}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_image_size(image: str) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--format", "{{.Size}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "-"


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
        rows: list[tuple[str, str, str, str, str]] = [(s.image, s.state, s.local, s.remote, s.size) for s in images]
    sha_len: int = find_unique_sha_length([r[2] for r in rows] + [r[3] for r in rows])
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
