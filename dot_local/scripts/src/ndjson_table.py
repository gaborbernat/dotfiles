# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "rich>=14.2",
# ]
# ///
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table


def main() -> None:
    parser = argparse.ArgumentParser(description="Display NDJSON as a rich table.")
    parser.add_argument("-f", dest="file", default=None, help="Path to the NDJSON file (default: stdin)")
    parser.add_argument("-c", "--columns", help="List of columns to display (space-separated)", nargs="+")
    parser.add_argument("-p", "--pivot", action="store_true", help="Pivot table: swap rows and columns")
    parser.add_argument(
        "-s", "--search", help="Search for a value in any row (can be repeated)", nargs="*", default=None
    )
    args = parser.parse_args()
    ndjson_table(args.file, selected_columns=args.columns, pivot=args.pivot, search=args.search)


def ndjson_table(  # noqa: C901, PLR0912, PLR0915
    filepath: str | None,
    selected_columns: list[str] | None = None,
    *,
    pivot: bool = False,
    search: list[str] | None = None,
) -> None:
    console: Console = Console()
    if filepath is None:
        lines: list[str] = list(sys.stdin)
    else:
        try:
            lines = Path(filepath).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            console.print(f"[bold red]Error:[/bold red] Cannot read {filepath}: {exc}")
            return

    if not lines:
        console.print("[bold red]Error:[/bold red] Empty input.")
        return

    first_obj = parse_json_object(lines[0])
    if first_obj is None:
        console.print("[bold red]Error:[/bold red] First line is not a JSON object.")
        return

    def flatten(obj: dict[str, object], parent_key: str = "") -> dict[str, object]:
        items: dict[str, object] = {}
        for key, value in obj.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                items.update(flatten(value, new_key))  # pyright: ignore [reportUnknownArgumentType]
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                items.update(flatten(value[0], new_key))  # pyright: ignore [reportUnknownArgumentType]
            else:
                items[new_key] = value
        return items

    flat_first_obj = flatten(first_obj)
    all_headers: list[str] = list(flat_first_obj.keys())
    headers: list[str] = selected_columns or all_headers
    type_map: dict[str, type] = {key: type(flat_first_obj[key]) for key in headers if key in flat_first_obj}

    try:
        patterns = [re.compile(pattern) for pattern in search or []]
    except re.error as exc:
        console.print(f"[bold red]Error:[/bold red] Invalid --search regex: {exc}")
        return

    # Collect all flattened rows
    flat_rows: list[dict[str, object]] = []
    for line in lines:
        if not line.strip():
            continue
        obj = parse_json_object(line)
        if obj is None:
            console.print(f"[yellow]Skipping non-object JSON line:[/yellow] {line.strip()}")
            continue
        flat_obj = flatten(obj)
        search_values = (
            [str(flat_obj.get(col, "")) for col in headers] if selected_columns else [str(v) for v in flat_obj.values()]
        )
        if patterns and not all(any(pat.search(v) for v in search_values) for pat in patterns):
            continue
        flat_rows.append(flat_obj)

    # Filter out columns that are entirely empty: None, "", or numeric zero (but never boolean False)
    def is_empty_column(key: str) -> bool:
        for row in flat_rows:
            value = row.get(key)
            if value is None or value == "":
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value == 0:
                continue
            return False
        return True

    filtered_headers: list[str] = [key for key in headers if not is_empty_column(key)]

    table: Table = Table(show_header=True, header_style="bold cyan")
    if not pivot:
        # Add sequence number as the first column
        table.add_column("#", no_wrap=True, style="dim", justify="right")
        for header in filtered_headers:
            table.add_column(header, no_wrap=True)
        for at, flat_obj in enumerate(flat_rows, 1):
            row = [str(at)] + [format_value(col, flat_obj.get(col, None), type_map) for col in filtered_headers]
            table.add_row(*row)
    else:
        # Pivot: columns become rows, rows become columns
        table.add_column("Field", no_wrap=True)
        for at in range(len(flat_rows)):
            table.add_column(f"Row {at + 1}", no_wrap=True)
        for col in filtered_headers:
            values = [format_value(col, flat_obj.get(col, None), type_map) for flat_obj in flat_rows]
            table.add_row(col, *values)

    console.print(table)


def parse_json_object(line: str) -> dict[str, object] | None:
    """Parse an NDJSON line, returning the object or None if it is invalid or not a JSON object."""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def human_readable_size(size: float) -> str:
    if size < 1024:
        return f"{size} B"
    for unit in ["KB", "MB", "GB", "TB", "PB"]:
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.2f} {unit}"
    return f"{size:.2f} PB"


def format_value(key: str, value: Any, type_map: dict[str, type]) -> str:  # noqa: ANN401
    if value is None:
        return ""
    col_type = type_map.get(key, type(value))  # pyright: ignore [reportUnknownArgumentType]
    if key == "size" and isinstance(value, int):
        return human_readable_size(value)
    if col_type in [int, float] and isinstance(value, (int, float)):
        return f"{value:_}"
    return str(value)


if __name__ == "__main__":
    main()
