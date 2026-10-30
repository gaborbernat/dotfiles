# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=15.0.0",
# ]
# ///
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Final

from rich.console import Console
from rich.table import Table

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


def main() -> None:
    parser: Final = argparse.ArgumentParser(description="Display NDJSON as a rich table.")
    parser.add_argument("-f", dest="file", help="Path to the NDJSON file (default: stdin)")
    parser.add_argument("-c", "--columns", help="List of columns to display (space-separated)", nargs="+")
    parser.add_argument("-p", "--pivot", action="store_true", help="Pivot table: swap rows and columns")
    parser.add_argument("-s", "--search", help="Search for a value in any row (can be repeated)", nargs="*")
    opts: Final = parser.parse_args(namespace=Options())
    ndjson_table(opts.file, opts.columns, pivot=opts.pivot, search=opts.search)


class Options(argparse.Namespace):
    file: str | None
    columns: list[str] | None
    pivot: bool
    search: list[str] | None


def ndjson_table(
    filepath: str | None, selected_columns: list[str] | None, *, pivot: bool, search: list[str] | None
) -> None:
    console: Final = Console()
    if filepath is None:
        lines = list(sys.stdin)
    else:
        try:
            lines = Path(filepath).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            console.print(f"[bold red]Error:[/bold red] Cannot read {filepath}: {exc}")
            return
    if not lines:
        console.print("[bold red]Error:[/bold red] Empty input.")
        return
    if (first_obj := parse_json_object(lines[0])) is None:
        console.print("[bold red]Error:[/bold red] First line is not a JSON object.")
        return
    try:
        patterns: Final = [re.compile(pattern) for pattern in search or []]
    except re.error as exc:
        console.print(f"[bold red]Error:[/bold red] Invalid --search regex: {exc}")
        return
    flat_first_obj: Final = flatten(first_obj)
    headers: Final = selected_columns or list(flat_first_obj)
    rows: Final = matching_rows(console, lines, selected_columns, patterns)
    console.print(
        build_table(
            rows,
            [key for key in headers if not all(is_blank(row.get(key)) for row in rows)],
            {key: type(flat_first_obj[key]) for key in headers if key in flat_first_obj},
            pivot=pivot,
        )
    )


def parse_json_object(line: str) -> dict[str, JsonValue] | None:
    try:
        obj: Final = json.loads(line)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def flatten(obj: dict[str, JsonValue], parent_key: str = "") -> dict[str, JsonValue]:
    items: Final[dict[str, JsonValue]] = {}
    for key, value in obj.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten(value, new_key))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            items.update(flatten(value[0], new_key))
        else:
            items[new_key] = value
    return items


def matching_rows(
    console: Console, lines: list[str], search_columns: list[str] | None, patterns: list[re.Pattern[str]]
) -> list[dict[str, JsonValue]]:
    rows: Final[list[dict[str, JsonValue]]] = []
    for line in lines:
        if not line.strip():
            continue
        if (obj := parse_json_object(line)) is None:
            console.print(f"[yellow]Skipping non-object JSON line:[/yellow] {line.strip()}")
            continue
        flat_obj = flatten(obj)
        values = (
            [str(flat_obj.get(col, "")) for col in search_columns]
            if search_columns
            else [str(value) for value in flat_obj.values()]
        )
        if all(any(pattern.search(value) for value in values) for pattern in patterns):
            rows.append(flat_obj)
    return rows


def is_blank(value: JsonValue) -> bool:
    # bool subclasses int, and False is a value rather than an empty cell
    return (
        value is None or value == "" or (isinstance(value, int | float) and not isinstance(value, bool) and value == 0)
    )


def build_table(
    rows: list[dict[str, JsonValue]], headers: list[str], type_map: dict[str, type], *, pivot: bool
) -> Table:
    table: Final = Table(show_header=True, header_style="bold cyan")
    if pivot:
        table.add_column("Field", no_wrap=True)
        for at in range(1, len(rows) + 1):
            table.add_column(f"Row {at}", no_wrap=True)
        for col in headers:
            table.add_row(col, *(format_value(col, row.get(col), type_map) for row in rows))
    else:
        table.add_column("#", no_wrap=True, style="dim", justify="right")
        for header in headers:
            table.add_column(header, no_wrap=True)
        for at, row in enumerate(rows, 1):
            table.add_row(str(at), *(format_value(col, row.get(col), type_map) for col in headers))
    return table


def format_value(key: str, value: JsonValue, type_map: dict[str, type]) -> str:
    if value is None:
        return ""
    if key == "size" and isinstance(value, int):
        return human_readable_size(value)
    if type_map.get(key, type(value)) in {int, float} and isinstance(value, int | float):
        return f"{value:_}"
    return str(value)


def human_readable_size(size: float) -> str:
    if size < 1024:
        return f"{size} B"
    for unit in ("KB", "MB", "GB", "TB", "PB"):
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.2f} {unit}"
    return f"{size:.2f} PB"


if __name__ == "__main__":
    main()
