# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=15.0.0",
# ]
# ///
import os
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Final

from rich.console import Console


def main() -> None:
    script_dir: Final = Path(__file__).parents[1].resolve()
    deps: Final = {dep for pyfile in (script_dir / "src").glob("*.py") for dep in extract_pep723_deps(pyfile)}
    if (pyproject := script_dir / "pyproject.toml").exists():
        deps.update(extract_pyproject_deps(pyproject))
    console: Final = Console()
    if not deps:
        console.print("[yellow]No dependencies found.[/yellow]")
        return
    console.print(f"[cyan]Creating venv and installing:[/cyan] [bold]{' '.join(deps)}[/bold]")
    subprocess.run(["uv", "venv", "--clear"], check=True, cwd=script_dir)
    venv_dir: Final = script_dir / ".venv"
    console.print(f"[green]Venv location:[/green] [bold]{venv_dir}[/bold]")
    env: Final = {**os.environ, "VIRTUAL_ENV": str(venv_dir)}
    subprocess.run(["uv", "pip", "install", *deps], check=True, cwd=script_dir, env=env)


def extract_pep723_deps(pyfile: Path) -> list[str]:
    # Parse the block as TOML rather than by hand so extras (rich[jupyter]) and single-line arrays work.
    if not (match := re.search(r"(?m)^# /// script$\s(?P<body>(?:^#.*$\s)*?)^# ///$", pyfile.read_text("utf-8"))):
        return []
    body: Final = "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in match["body"].splitlines())
    try:
        data: Final = tomllib.loads(body)
    except tomllib.TOMLDecodeError:
        return []
    return [dep for dep in data.get("dependencies", []) if isinstance(dep, str)]


def extract_pyproject_deps(pyproject: Path) -> list[str]:
    data: Final = tomllib.loads(pyproject.read_text("utf-8"))
    project: Final = data.get("project", {})
    deps: Final[list[str]] = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        deps.extend(dep for dep in extra if isinstance(dep, str))
    for group in data.get("dependency-groups", {}).values():
        deps.extend(dep for dep in group if isinstance(dep, str))
    return deps


if __name__ == "__main__":
    main()
