#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Shrink pytest and tox output to what an agent acts on.

As a PreToolUse hook on Bash, ``rewrite`` pipes a plain pytest or tox command through ``filter``, which names a log of
the full output first, so a run killed by a timeout still leaves it, then prints the failures, errors, coverage gaps and
summaries.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path
from typing import Final

_TEST_COMMAND: Final[re.Pattern[str]] = re.compile(
    r"^(?:uv run (?:\S+ )*?)?(?:\S*/)?(?:pytest|tox|python3? -m pytest)(?:\s|$)"
)
_SHELL_SYNTAX: Final[re.Pattern[str]] = re.compile(r"[|<>;&`#\n]|\$\(")
# pytest-cov before 6.0 opens its report with a dashed rule instead of a section line.
_SECTION: Final[re.Pattern[str]] = re.compile(r"^(?:=+ (?P<title>.+?) =+|-+ coverage: .+ -+)$")
_KEPT_SECTIONS: Final[tuple[str, ...]] = ("FAILURES", "ERRORS", "short test summary info")
_COVERAGE_ROW: Final[re.Pattern[str]] = re.compile(r"^\S+(?:\s+\d+){2,4}\s+(?P<cover>\d+(?:\.\d+)?)%")
_KEPT_LINE: Final[re.Pattern[str]] = re.compile(
    r"^(?:ERROR|FAILED|FAIL Required|Name\s+Stmts|TOTAL\s)|^\s*\S+: (?:OK|FAIL|SKIP|exit -?\d+)|congratulations|"
    r"evaluation failed"
)
_SHORT_OUTPUT: Final[int] = 60
_TAIL: Final[int] = 5
_FALLBACK_TAIL: Final[int] = 80
_LOG_DIR: Final[Path] = Path.home() / ".cache" / "claude" / "test-output"
_LOG_MAX_AGE: Final[float] = 24 * 3600


def rewrite(event: dict[str, object]) -> dict[str, object] | None:
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict) or not isinstance(command := tool_input.get("command"), str):
        return None
    # A pipe, redirect or chain already shapes the output, and wrapping it could change what the command means.
    if not _TEST_COMMAND.match(command.strip()) or _SHELL_SYNTAX.search(command):
        return None
    script = shlex.quote(str(Path(__file__).resolve()))
    piped = f"( set -o pipefail; {command.strip()} 2>&1 | {script} filter )"
    # The rewritten command no longer matches the user's own rules, so approve the test run it wraps explicitly
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "test run, output filtered to failures",
            "updatedInput": {**tool_input, "command": piped},
        }
    }


def condense(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= _SHORT_OUTPUT:
        return text
    kept: set[int] = set()
    in_section = False
    for index, line in enumerate(lines):
        if section := _SECTION.match(line):
            in_section = section["title"] in _KEPT_SECTIONS
            kept.add(index)  # the final "N passed in Xs" summary is also a section line
        elif (
            in_section or _KEPT_LINE.search(line) or ((row := _COVERAGE_ROW.match(line)) and float(row["cover"]) < 100)
        ):
            kept.add(index)
    if not kept:
        kept = set(range(max(0, len(lines) - _FALLBACK_TAIL), len(lines)))
    kept |= set(range(len(lines) - _TAIL, len(lines)))
    excerpt = "\n".join(lines[index] for index in sorted(kept))
    return f"[test output filtered: {len(kept)} of {len(lines)} lines kept]\n{excerpt}\n"


def _new_log() -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - _LOG_MAX_AGE
    for old in _LOG_DIR.glob("*.log"):
        # Another filter running at the same time may prune the same file first
        with contextlib.suppress(FileNotFoundError):
            if old.stat().st_mtime < cutoff:
                old.unlink()
    return _LOG_DIR / f"{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}.log"


def main(argv: list[str]) -> int:
    match argv:
        case ["rewrite"]:
            if (output := rewrite(json.load(sys.stdin))) is not None:
                json.dump(output, sys.stdout)
        case ["filter"]:
            log = _new_log()
            sys.stdout.write(f"[full test output: {log}]\n")
            sys.stdout.flush()
            with log.open("wb") as sink:
                while chunk := sys.stdin.buffer.read1():
                    sink.write(chunk)
                    sink.flush()
            # Tests may print bytes that are not UTF-8; showing them replaced beats losing the whole run
            sys.stdout.write(condense(log.read_bytes().decode("utf-8", errors="replace")))
        case _:
            sys.stderr.write("usage: filter-test-output.py rewrite|filter\n")
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
