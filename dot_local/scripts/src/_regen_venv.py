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
    # The PEP 723 block is TOML behind `# ` comment prefixes; parse it as TOML rather than by hand so
    # extras (rich[jupyter]) and single-line arrays are handled correctly.
    if not (match := re.search(r"(?m)^# /// script$\s(?P<body>(?:^#.*$\s)*?)^# ///$", pyfile.read_text("utf-8"))):
        return []
    body = "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in match["body"].splitlines())
    try:
        data = tomllib.loads(body)
    except tomllib.TOMLDecodeError:
        return []
    return [dep for dep in data.get("dependencies", []) if isinstance(dep, str)]


def extract_pyproject_deps(pyproject: Path) -> list[str]:
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    project = data.get("project", {})
    deps: list[str] = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        deps.extend(d for d in extra if isinstance(d, str))
    for group in data.get("dependency-groups", {}).values():
        deps.extend(d for d in group if isinstance(d, str))
    return deps


if __name__ == "__main__":
    main()
