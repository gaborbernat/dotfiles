# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=15.0.0",
#     "packaging>=26.3",
# ]
# ///
import argparse
import json
import subprocess
from typing import Final, Literal, TypedDict

from packaging.version import Version
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

type Variant = Literal["default", "freethreaded"]

_CONSOLE: Final = Console()


def main() -> None:
    parser: Final = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print commands instead of executing them")
    opts: Final = parser.parse_args(namespace=Options())

    _CONSOLE.print("[bold cyan]🔁 Checking and updating Python versions using uv...[/]")
    available: Final = parse_available_versions()
    currently_installed: Final = installed_versions()
    results: Final[list[tuple[str, str, str, str]]] = []
    obsolete: Final[set[str]] = set()
    failed = False
    versions: Final = [v for i in range(15, 7, -1) for v in ([f"3.{i}", f"3.{i}t"] if i >= 14 else [f"3.{i}"])]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        transient=True,
        console=_CONSOLE,
    ) as progress:
        task = progress.add_task("Checking Python versions...", total=len(versions))
        for version in versions:
            progress.update(task, description=f"🔍 Finding latest patch version for Python {version}...")
            variant: Variant = "freethreaded" if version.endswith("t") else "default"
            base_version = Version(version.removesuffix("t"))
            latest = find_latest_version(available, base_version, variant)
            installed_for_minor = find_installed_for_minor(currently_installed, base_version, variant)

            if not latest:
                results.append((version, "-", "[red]Not found[/]", installed_for_minor))
                progress.advance(task)
                continue
            if already_installed := latest in currently_installed:
                installed_ok = True
                status = "[green]Already installed[/]"
            elif opts.dry_run:
                installed_ok = install_python(latest, dry_run=True)
                status = "[green](Dry run) Would install[/]"
            else:
                with _CONSOLE.status(f"[bold blue]⬇️  Installing Python variant: {latest}..."):
                    installed_ok = install_python(latest, dry_run=False)
                status = "[green]Installed[/]" if installed_ok else "[red]Install failed[/]"

            if installed_ok:
                obsolete.update(obsolete_versions(currently_installed, latest))
            else:
                failed = True

            results.append((version, latest, status, installed_for_minor))

            # uv tools run on this minor version
            if (
                version == "3.14"
                and not already_installed
                and installed_ok
                and not upgrade_tools(latest, dry_run=opts.dry_run)
            ):
                failed = True
            progress.advance(task)

    print_results(results)
    if failed:
        msg = "Python update failed; installed versions were kept"
        raise SystemExit(msg)
    if not remove_obsolete_versions(obsolete, dry_run=opts.dry_run):
        msg = "Python update failed while removing old versions"
        raise SystemExit(msg)
    _CONSOLE.print("[bold green]✅ All done.[/]")


class Options(argparse.Namespace):
    dry_run: bool


class UvPython(TypedDict):
    implementation: str
    variant: str
    version: str
    version_parts: dict[str, int]


def parse_available_versions() -> list[UvPython]:
    output: Final = run_uv_command(["uv", "python", "list", "--only-downloads", "--output-format", "json"])
    if not output:
        msg = "uv returned no Python download catalog; no versions were changed"
        raise SystemExit(msg)
    entries: Final[list[UvPython]] = json.loads(output)
    if not (available := [entry for entry in entries if entry["implementation"] == "cpython"]):
        msg = "uv returned an empty Python download catalog; no versions were changed"
        raise SystemExit(msg)
    return available


def run_uv_command(cmd: list[str]) -> str | None:
    try:
        result: Final = subprocess.run(cmd, capture_output=True, check=True, text=True, timeout=1800)
    except subprocess.CalledProcessError as error:
        _CONSOLE.print(f"[red]Command failed:[/] {' '.join(cmd)}")
        if error.stderr:
            _CONSOLE.print(f"[red]{error.stderr.strip()}[/]")
        return None
    except subprocess.TimeoutExpired:
        _CONSOLE.print(f"[red]Command timed out:[/] {' '.join(cmd)}")
        return None
    return result.stdout


def installed_versions() -> set[str]:
    output: Final = run_uv_command([
        "uv",
        "python",
        "list",
        "--only-installed",
        "--managed-python",
        "--output-format",
        "json",
    ])
    if output is None:
        msg = "uv could not list installed Python versions; no versions were changed"
        raise SystemExit(msg)
    entries: Final[list[UvPython]] = json.loads(output)
    return {
        f"{entry['version']}{'t' if entry['variant'] == 'freethreaded' else ''}"
        for entry in entries
        if entry["implementation"] == "cpython"
    }


def find_latest_version(available: list[UvPython], version: Version, variant: Variant) -> str | None:
    candidates: Final = {
        entry["version"]
        for entry in available
        if entry["variant"] == variant and entry["version_parts"]["minor"] == version.minor
    }
    if not candidates:
        return None
    return f"{max(candidates, key=Version)}{'t' if variant == 'freethreaded' else ''}"


def find_installed_for_minor(installed: set[str], version: Version, variant: Variant) -> str:
    matches: Final = sorted(
        (
            v
            for v in installed
            if v.endswith("t") == (variant == "freethreaded") and Version(v.removesuffix("t")).minor == version.minor
        ),
        key=lambda v: Version(v.removesuffix("t")),
        reverse=True,
    )
    return ", ".join(matches) if matches else "-"


def install_python(key: str, *, dry_run: bool) -> bool:
    cmd: Final = ["uv", "python", "install", key]
    if dry_run:
        _CONSOLE.print(f"[blue]DRY RUN:[/] {' '.join(cmd)}")
        return True
    return run_uv_command(cmd) is not None


def obsolete_versions(installed: set[str], latest: str) -> set[str]:
    target: Final = Version(latest.removesuffix("t"))
    return {
        candidate
        for candidate in installed
        if candidate != latest
        and candidate.endswith("t") == latest.endswith("t")
        and Version(candidate.removesuffix("t")).minor == target.minor
    }


def upgrade_tools(version: str, *, dry_run: bool) -> bool:
    cmd: Final = ["uv", "tool", "upgrade", "--all", "-p", version]
    _CONSOLE.print(f"[cyan]♻️  Upgrading all tools for Python {version}...[/]")
    if dry_run:
        _CONSOLE.print(f"[blue]DRY RUN:[/] {' '.join(cmd)}")
        return True
    if run_uv_command(cmd) is None:
        return False
    _CONSOLE.print(f"[green]🔧 Tools upgraded for Python {version}[/]")
    return True


def print_results(results: list[tuple[str, str, str, str]]) -> None:
    table: Final = Table(title="Python Version Update Summary")
    table.add_column("Version", style="cyan", justify="right")
    table.add_column("Latest Patch", style="magenta")
    table.add_column("Installed", style="dim")
    table.add_column("Status", style="green")
    for version, latest, status, installed_for_minor in results:
        table.add_row(version, latest, installed_for_minor, status)
    _CONSOLE.print(table)


def remove_obsolete_versions(obsolete: set[str], *, dry_run: bool) -> bool:
    succeeded = True
    for extra in sorted(obsolete):
        _CONSOLE.print("Uninstall extra version:", extra)
        if dry_run:
            _CONSOLE.print(f"[blue]DRY RUN:[/] uv python uninstall {extra}")
        elif run_uv_command(["uv", "python", "uninstall", extra]) is None:
            succeeded = False
    return succeeded


if __name__ == "__main__":
    main()
