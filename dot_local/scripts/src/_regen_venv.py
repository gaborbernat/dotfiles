# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
from __future__ import annotations

import os
import re
import subprocess
import tomllib
from pathlib import Path

from rich.console import Console

console = Console()


def main() -> None:
    script_dir = Path(__file__).parents[1].resolve()
    deps: set[str] = set()
    for pyfile in (script_dir / "src").glob("*.py"):
        deps.update(extract_pep723_deps(pyfile))
    pyproject = script_dir / "pyproject.toml"
    if pyproject.exists():
        deps.update(extract_pyproject_deps(pyproject))
    if not deps:
        console.print("[yellow]No dependencies found.[/yellow]")
        return
    console.print(f"[cyan]Creating venv and installing:[/cyan] [bold]{' '.join(deps)}[/bold]")
    subprocess.run(["uv", "venv", "--clear"], check=True, cwd=script_dir)
    venv_dir = script_dir / ".venv"
    console.print(f"[green]Venv location:[/green] [bold]{venv_dir}[/bold]")
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(venv_dir)
    subprocess.run(["uv", "pip", "install", *deps], check=True, cwd=script_dir, env=env)


def extract_pep723_deps(pyfile: Path) -> list[str]:
    deps = []
    in_block = False
    in_deps = False
    with pyfile.open(encoding="utf-8") as f:
        for line in f:
            if re.match(r"#\s*///\s*script", line):
                in_block = True
            elif in_block and re.match(r"#\s*///", line):
                in_block = False
            elif in_block and re.match(r"#\s*dependencies\s*=\s*\[", line):
                in_deps = True
            elif in_deps and "]" in line:
                in_deps = False
            elif in_deps and (match := re.search(r'"([^"]+)"', line)):
                deps.append(match.group(1))
    return deps


def extract_pyproject_deps(pyproject: Path) -> list[str]:
    deps: list[str] = []
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    groups = data.get("dependency-groups", {})
    for group in groups.values():
        deps.extend(group)
    return deps


if __name__ == "__main__":
    main()
