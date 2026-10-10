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
from typing import Any, Final, Literal

from packaging.version import Version
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

VERSIONS: Final[list[str]] = [v for i in range(15, 7, -1) for v in ([f"3.{i}", f"3.{i}t"] if i >= 14 else [f"3.{i}"])]
TOOL_VERSION: Final[str] = "3.14"
CONSOLE: Final[Console] = Console()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print commands instead of executing them")
    args = parser.parse_args()
    dry_run = args.dry_run

    CONSOLE.print("[bold cyan]🔁 Checking and updating Python versions using uv...[/]")
    available = parse_available_versions()
    currently_installed = installed_version()
    results: list[tuple[str, str, str, str]] = []
    obsolete: set[str] = set()
    failed = False

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        transient=True,
        console=CONSOLE,
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
            if already_installed := latest in currently_installed:
                installed_ok = True
                status = "[green]Already installed[/]"
            elif dry_run:
                installed_ok = install_python(latest, dry_run=dry_run)
                status = "[green](Dry run) Would install[/]"
            else:
                with CONSOLE.status(f"[bold blue]⬇️  Installing Python variant: {latest}..."):
                    installed_ok = install_python(latest)
                status = "[green]Installed[/]" if installed_ok else "[red]Install failed[/]"

            if installed_ok:
                obsolete.update(obsolete_versions(currently_installed, latest))
            else:
                failed = True

            results.append((version, latest, status, installed_for_minor))

            if (
                version == TOOL_VERSION
                and not already_installed
                and installed_ok
                and not upgrade_tools(latest, dry_run=dry_run)
            ):
                failed = True
            progress.advance(task)

    print_results(results)
    if failed:
        msg = "Python update failed; installed versions were kept"
        raise SystemExit(msg)
    if not remove_obsolete_versions(obsolete, dry_run=dry_run):
        msg = "Python update failed while removing old versions"
        raise SystemExit(msg)
    CONSOLE.print("[bold green]✅ All done.[/]")


def print_results(results: list[tuple[str, str, str, str]]) -> None:
    table = Table(title="Python Version Update Summary")
    table.add_column("Version", style="cyan", justify="right")
    table.add_column("Latest Patch", style="magenta")
    table.add_column("Installed", style="dim")
    table.add_column("Status", style="green")

    for version, latest, status, installed_for_minor in results:
        table.add_row(version, latest, installed_for_minor, status)
    CONSOLE.print(table)


def remove_obsolete_versions(obsolete: set[str], *, dry_run: bool) -> bool:
    succeeded = True
    for extra in sorted(obsolete):
        CONSOLE.print("Uninstall extra version:", extra)
        if dry_run:
            CONSOLE.print(f"[blue]DRY RUN:[/] uv python uninstall {extra}")
        elif run_uv_command(["uv", "python", "uninstall", extra]) is None:
            succeeded = False
    return succeeded


def obsolete_versions(installed: set[str], latest: str) -> set[str]:
    target = Version(latest.removesuffix("t"))
    return {
        candidate
        for candidate in installed
        if candidate != latest
        and candidate.endswith("t") == latest.endswith("t")
        and Version(candidate.removesuffix("t")).minor == target.minor
    }


def parse_available_versions() -> list[dict[str, Any]]:
    output = run_uv_command(["uv", "python", "list", "--only-downloads", "--output-format", "json"])
    if not output:
        msg = "uv returned no Python download catalog; no versions were changed"
        raise SystemExit(msg)
    available: list[dict[str, Any]] = [item for item in json.loads(output) if item["implementation"] == "cpython"]
    if not available:
        msg = "uv returned an empty Python download catalog; no versions were changed"
        raise SystemExit(msg)
    return available


def installed_version() -> set[str]:
    output = run_uv_command(["uv", "python", "list", "--only-installed", "--managed-python", "--output-format", "json"])
    if output is None:
        msg = "uv could not list installed Python versions; no versions were changed"
        raise SystemExit(msg)
    return {
        f"{i['version']}{'t' if i['variant'] == 'freethreaded' else ''}"
        for i in json.loads(output)
        if i["implementation"] == "cpython"
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
    latest = max(candidates, key=Version)
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


def install_python(key: str, *, dry_run: bool = False) -> bool:
    cmd = ["uv", "python", "install", key]
    if dry_run:
        CONSOLE.print(f"[blue]DRY RUN:[/] {' '.join(cmd)}")
        return True
    return run_uv_command(cmd) is not None


def upgrade_tools(version: str, *, dry_run: bool = False) -> bool:
    cmd = ["uv", "tool", "upgrade", "--all", "-p", version]
    CONSOLE.print(f"[cyan]♻️  Upgrading all tools for Python {version}...[/]")
    if dry_run:
        CONSOLE.print(f"[blue]DRY RUN:[/] {' '.join(cmd)}")
        return True
    if run_uv_command(cmd) is None:
        return False
    CONSOLE.print(f"[green]🔧 Tools upgraded for Python {version}[/]")
    return True


def run_uv_command(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True, timeout=1800)
        return result.stdout  # noqa: TRY300
    except subprocess.CalledProcessError as e:
        CONSOLE.print(f"[red]Command failed:[/] {' '.join(cmd)}")
        if e.stderr:
            CONSOLE.print(f"[red]{e.stderr.strip()}[/]")
        return None
    except subprocess.TimeoutExpired:
        CONSOLE.print(f"[red]Command timed out:[/] {' '.join(cmd)}")
        return None


if __name__ == "__main__":
    main()
