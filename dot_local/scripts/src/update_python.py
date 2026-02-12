# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
#     "packaging>=25",
# ]
# ///
from __future__ import annotations

import argparse
import json
import subprocess
from functools import cache
from pathlib import Path
from typing import Any, Final, Literal

from packaging.version import Version
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

VERSIONS: Final[list[str]] = [v for i in range(15, 7, -1) for v in ([f"3.{i}", f"3.{i}t"] if i >= 14 else [f"3.{i}"])]
TOOL_VERSION: Final[str] = "3.14"
console: Final[Console] = Console()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print commands instead of executing them")
    args = parser.parse_args()
    dry_run = args.dry_run

    console.print("[bold cyan]🔁 Checking and updating Python versions using uv...[/]")
    available = parse_available_versions()
    currently_installed = installed_version()
    results: list[tuple[str, str, str, str]] = []
    installed_versions: set[str] = set()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("Checking Python versions...", total=len(VERSIONS))
        for version in VERSIONS:
            progress.update(task, description=f"🔍 Finding latest patch version for Python {version}...")
            variant: Literal["freethreaded", "default"] = "freethreaded" if version.endswith("t") else "default"
            base_version = Version(version.removesuffix("t"))
            latest = find_latest_version(available, base_version, variant=variant)
            installed_for_minor = find_installed_for_minor(currently_installed, base_version, variant=variant)

            if not latest:
                results.append((version, "-", "[red]Not found[/]", installed_for_minor))
                progress.advance(task)
                continue
            installed_versions.add(latest)

            if already_installed := latest in currently_installed:
                status = "[green]Already installed[/]"
            else:
                with console.status(f"[bold blue]⬇️  Installing Python variant: {latest}..."):
                    install_python(latest, dry_run=dry_run)
                status = "[green]Installed[/]" if not dry_run else "[green](Dry run) Would install[/]"

            results.append((version, latest, status, installed_for_minor))

            if version == TOOL_VERSION and not already_installed:
                upgrade_tools(latest, dry_run=dry_run)
            progress.advance(task)

    table = Table(title="Python Version Update Summary")
    table.add_column("Version", style="cyan", justify="right")
    table.add_column("Latest Patch", style="magenta")
    table.add_column("Installed", style="dim")
    table.add_column("Status", style="green")

    for version, latest, status, installed_for_minor in results:
        table.add_row(version, latest, installed_for_minor, status)
    console.print(table)

    for extra in installed_version() - installed_versions:
        console.print("Uninstall extra version:", extra)
        run_uv_command(["uv", "python", "uninstall", extra])
    console.print("[bold green]✅ All done.[/]")


@cache
def parse_available_versions() -> list[dict[str, Any]]:
    output = run_uv_command(["uv", "python", "list", "--managed-python", "--output-format", "json"])
    return json.loads(output) if output else []


@cache
def installed_version() -> set[str]:
    return {
        f"{i['version']}{'t' if i['variant'] == 'freethreaded' else ''}"
        for i in parse_available_versions()
        if (i["path"] or "").startswith(str(Path.home() / ".local" / "share" / "uv" / "python"))
    }


def find_latest_version(
    available: list[dict[str, Any]], version: Version, variant: Literal["default", "freethreaded"]
) -> str | None:
    candidates = {
        entry["version"]
        for entry in available
        if entry["variant"] == variant and entry["version_parts"]["minor"] == version.minor
    }
    if not candidates:
        return None
    latest = sorted(candidates, key=Version)[-1]
    return f"{latest}{'t' if variant == 'freethreaded' else ''}"


def find_installed_for_minor(installed: set[str], version: Version, variant: Literal["default", "freethreaded"]) -> str:
    is_freethreaded = variant == "freethreaded"
    matches = sorted(
        (
            v
            for v in installed
            if v.endswith("t") == is_freethreaded and Version(v.removesuffix("t")).minor == version.minor
        ),
        key=lambda v: Version(v.removesuffix("t")),
        reverse=True,
    )
    return ", ".join(matches) if matches else "-"


def install_python(key: str, *, dry_run: bool = False) -> None:
    cmd = ["uv", "python", "install", key]
    if dry_run:
        console.print(f"[blue]DRY RUN:[/] {' '.join(cmd)}")
    else:
        run_uv_command(cmd)


def upgrade_tools(version: str, *, dry_run: bool = False) -> None:
    cmd = ["uv", "tool", "upgrade", "--all", "-p", version]
    console.print(f"[cyan]♻️  Upgrading all tools for Python {version}...[/]")
    if dry_run:
        console.print(f"[blue]DRY RUN:[/] {' '.join(cmd)}")
    else:
        run_uv_command(cmd)
    console.print(f"[green]🔧 Tools upgraded for Python {version}[/]")


def run_uv_command(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        return result.stdout  # noqa: TRY300
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed:[/] {' '.join(cmd)}")
        if e.stderr:
            console.print(f"[red]{e.stderr.strip()}[/]")
        return ""


if __name__ == "__main__":
    main()
