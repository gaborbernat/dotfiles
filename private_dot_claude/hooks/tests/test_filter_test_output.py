from __future__ import annotations

import importlib.util
import io
import json
import os
import runpy
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_SCRIPT: Final[Path] = Path(__file__).parents[1] / "executable_filter-test-output.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("filter_test_output", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ftp: Final = _load()


def _event(command: object) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command, "description": "Run tests"}}


@pytest.mark.parametrize(
    "command",
    [
        pytest.param("pytest", id="pytest"),
        pytest.param("pytest -x tests/unit", id="pytest-args"),
        pytest.param("tox -e 3.14", id="tox"),
        pytest.param(".tox/dev/bin/python -m pytest tests", id="tox-dev-python"),
        pytest.param("uv run --with pytest pytest -x", id="uv-run"),
        pytest.param("  pytest  ", id="padded"),
    ],
)
def test_rewrite_pipes_test_command(command: str) -> None:
    script = str(_SCRIPT.resolve())
    expected = f"( set -o pipefail; {command.strip()} 2>&1 | {script} filter )"
    hook_output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {"command": expected, "description": "Run tests"},
        }
    }
    assert ftp.rewrite(_event(command)) == hook_output


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(_event("ls -la"), id="not-a-test"),
        pytest.param(_event("pytest | tail -20"), id="piped"),
        pytest.param(_event("pytest > out.txt"), id="redirected"),
        pytest.param(_event("pytest && echo done"), id="chained"),
        pytest.param(_event("pytest; echo done"), id="sequenced"),
        pytest.param(_event("pytest $(git diff --name-only)"), id="substitution"),
        pytest.param(_event("pytest\necho done"), id="multiline"),
        pytest.param(_event("pytesting"), id="prefix-only"),
        pytest.param(_event(None), id="command-not-string"),
        pytest.param({"tool_name": "Bash"}, id="no-tool-input"),
    ],
)
def test_rewrite_leaves_other_commands(event: dict[str, object]) -> None:
    assert ftp.rewrite(event) is None


def test_condense_keeps_short_output_whole(tmp_path: Path) -> None:
    text = "===== 3 passed in 0.10s =====\n"
    assert ftp.condense(text, tmp_path / "x.log") == text


@pytest.mark.parametrize(
    "coverage_header",
    [
        pytest.param(
            [
                "================================ tests coverage ================================",
                "_______________ coverage: platform linux, python 3.14.0-final-0 ________________",
            ],
            id="pytest-cov-6",
        ),
        pytest.param(["---------- coverage: platform linux, python 3.14.0 ----------"], id="pytest-cov-5"),
    ],
)
def test_condense_keeps_failures_coverage_and_summary(coverage_header: list[str], tmp_path: Path) -> None:
    session = "============================= test session starts =============================="
    failures = [
        "=================================== FAILURES ===================================",
        "__________________________________ test_bad ___________________________________",
        "E       assert 1 == 2",
    ]
    covered = "src/a.py           10      0   100%"
    coverage_gaps = [
        "Name            Stmts   Miss  Cover   Missing",
        "src/b.py           10      2    80%   3-4",
        "TOTAL              20      2    90%",
        "FAIL Required test coverage of 100% not reached. Total coverage: 90.00%",
    ]
    summary = [
        "=========================== short test summary info ============================",
        "FAILED tests/test_a.py::test_bad - assert 1 == 2",
        "========================= 1 failed, 100 passed in 1.00s =========================",
        "  py: FAIL code 1 (2.00 seconds)",
        "  evaluation failed :( (2.10 seconds)",
    ]
    passing = [f"tests/test_a.py::test_{index} PASSED" for index in range(100)]
    lines = [session, *passing, *failures, *coverage_header, covered, *coverage_gaps, *summary]
    kept = [session, *failures, coverage_header[0], *coverage_gaps, *summary]
    log = tmp_path / "x.log"
    expected = f"[test output filtered: {len(kept)} of {len(lines)} lines kept; full output in {log}]\n"
    assert ftp.condense("\n".join(lines), log) == expected + "\n".join(kept) + "\n"


def test_condense_falls_back_to_tail(tmp_path: Path) -> None:
    lines = [f"line {index}" for index in range(100)]
    log = tmp_path / "x.log"
    expected = f"[test output filtered: 80 of 100 lines kept; full output in {log}]\n" + "\n".join(lines[20:]) + "\n"
    assert ftp.condense("\n".join(lines), log) == expected


def test_main_rewrite_prints_hook_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_event("tox"))))
    assert ftp.main(["rewrite"]) == 0
    assert json.loads(capsys.readouterr().out) == ftp.rewrite(_event("tox"))


def test_main_rewrite_prints_nothing_for_other_commands(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_event("ls"))))
    assert ftp.main(["rewrite"]) == 0
    assert not capsys.readouterr().out


def test_main_filter_logs_and_prunes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    stale, fresh = log_dir / "stale.log", log_dir / "fresh.log"
    stale.write_text("old")
    fresh.write_text("new")
    day_ago = time.time() - 2 * 24 * 3600
    os.utime(stale, (day_ago, day_ago))
    monkeypatch.setattr(ftp, "_LOG_DIR", log_dir)
    monkeypatch.setattr(sys, "stdin", io.StringIO("1 passed\n"))
    assert ftp.main(["filter"]) == 0
    assert capsys.readouterr().out == "1 passed\n"
    new_logs = set(log_dir.glob("*.log")) - {fresh}
    assert [path.read_text() for path in new_logs] == ["1 passed\n"]
    assert not stale.exists()


def test_main_usage(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", [str(_SCRIPT)])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(_SCRIPT), run_name="__main__")
    assert (exc_info.value.code, capsys.readouterr().err) == (2, "usage: filter-test-output.py rewrite|filter\n")


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_rewritten_command_keeps_exit_code(shell: str, tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "pytest"
    fake.write_text("#!/bin/sh\necho 'FAILED tests/test_a.py::test_bad'\nexit 3\n")
    fake.chmod(0o755)
    piped = ftp.rewrite(_event("pytest"))["hookSpecificOutput"]["updatedInput"]["command"]
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "HOME": str(tmp_path)}
    result = subprocess.run([shell, "-c", piped], capture_output=True, text=True, env=env, check=False)
    assert (result.returncode, result.stdout) == (3, "FAILED tests/test_a.py::test_bad\n")
