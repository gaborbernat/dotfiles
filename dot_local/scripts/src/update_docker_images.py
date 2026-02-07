# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich import box
from rich.console import Console
from rich.progress import MofNCompleteColumn, Progress, TextColumn
from rich.table import Table

console = Console()


def main() -> None:
    images: list[str] = get_images()
    table: Table = create_table()
    results: list[tuple[str, str, str, str, str]] = []
    with Progress(TextColumn("[progress.description]{task.description}"), MofNCompleteColumn()) as progress:
        task = progress.add_task("Checking images", total=len(images))
        with ThreadPoolExecutor() as executor:
            future_to_image = {executor.submit(process_image, image): image for image in images}
            for future in as_completed(future_to_image):
                image = future_to_image[future]
                try:
                    row = future.result()
                    results.append(row)
                except Exception as exc:  # noqa: BLE001
                    results.append((image, f"[red]Error: {exc}[/red]", "-", "-", "-"))
                progress.update(task, advance=1)
    # Sort results by image name
    results.sort(key=lambda row: row[0])
    for i, row in enumerate(results, 1):
        table.add_row(str(i), *row)
    console.print()
    console.print(table)


def get_images() -> list[str]:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    images = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or "<none>" in line:
            continue
        if has_remote_registry(line):
            images.append(line)
    return images


def has_remote_registry(image: str) -> bool:
    if not has_repo_digests(image):
        return False
    if is_private_registry(image):
        return True
    return exists_in_remote_registry(image)


def has_repo_digests(image: str) -> bool:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "inspect", "--format", "{{.RepoDigests}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() not in ("[]", "")


def is_private_registry(image: str) -> bool:
    repo = image.rsplit(":", 1)[0]
    first_segment = repo.split("/", 1)[0]
    return "/" in repo and ("." in first_segment or ":" in first_segment)


def exists_in_remote_registry(image: str) -> bool:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "manifest", "inspect", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def create_table() -> Table:
    table: Table = Table(title="Docker Image Update Summary", box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right")
    table.add_column("Image", style="bold")
    table.add_column("Status")
    table.add_column("Old SHA", overflow="fold")
    table.add_column("New SHA", overflow="fold")
    table.add_column("Size", justify="right")
    return table


def get_image_size(image: str) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--format", "{{.Size}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "-"


def process_image(image: str) -> tuple[str, str, str, str, str]:
    old_sha: str = get_sha(image)[7:]
    size: str = get_image_size(image)
    if docker_pull(image):
        new_sha: str = get_sha(image)[7:]
        if old_sha == new_sha:
            return image, "[blue]Unchanged[/blue]", old_sha, "", size
        return image, "[green]Updated[/green]", old_sha, new_sha, size
    return image, "[yellow]Pull failed[/yellow]", old_sha, "", size


def get_sha(image: str) -> str:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "images", "--no-trunc", "--format", "{{.ID}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def docker_pull(image: str) -> bool:
    result: subprocess.CompletedProcess[str] = subprocess.run(
        ["docker", "pull", image], check=False, capture_output=True, text=True
    )
    return result.returncode == 0


if __name__ == "__main__":
    main()
