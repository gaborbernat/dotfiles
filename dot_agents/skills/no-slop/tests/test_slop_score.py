from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

_SCRIPT: Final[Path] = Path(__file__).parents[1] / "scripts" / "slop_score.py"


def _run_score(text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(_SCRIPT)], input=text, text=True, capture_output=True, check=False)


@pytest.mark.parametrize(
    ("text", "category", "column"),
    [
        pytest.param("This matters because the cache is slow.\n", "emphasis", 1, id="emphasis"),
        pytest.param(
            "The cache finished, highlighting the importance of retries.\n", "participle-tail", 19, id="participle-tail"
        ),
        pytest.param("Let me walk you through the cache.\n", "setup-resolution", 1, id="setup-resolution"),
        pytest.param("It's about speed. It's about trust.\n", "anaphora", 1, id="anaphora"),
        pytest.param("Released on 2026-XX-XX.\n", "placeholder", 13, id="placeholder-date"),
        pytest.param("Released by INSERT_AUTHOR_NAME.\n", "placeholder", 13, id="placeholder-insert"),
    ],
)
def test_gate_reports_location(text: str, category: str, column: int) -> None:
    result = _run_score("The parser exits on error.\n" + text)
    assert result.returncode == 1
    assert f"<stdin>:2:{column}: {category}:" in result.stdout


def test_gate_reports_location_after_tilde_fence() -> None:
    result = _run_score("~~~python\nprint('this matters because')\n~~~~\nThis matters because retries can loop.\n")
    assert result.returncode == 1
    assert "<stdin>:4:1: emphasis:" in result.stdout


@pytest.mark.parametrize(
    "word",
    [
        pytest.param("nuanced", id="nuanced"),
        pytest.param("transformative", id="transformative"),
        pytest.param("underscored", id="underscored"),
        pytest.param("leveraged", id="leveraged"),
        pytest.param("fostered", id="fostered"),
        pytest.param("prioritized", id="prioritized"),
    ],
)
def test_stock_word_is_advisory(word: str) -> None:
    result = _run_score(f"The analysis is {word}.\n")
    assert result.returncode == 0
    assert "stock vocabulary" in result.stdout


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(
            "Use `this matters because` as input.\n```python\nprint('this matters because')\n```\n", id="markdown-code"
        ),
        pytest.param("Run the parser, renderer, and formatter.\n", id="literal-list"),
        pytest.param(
            "What if pip has to build from source? It creates an isolated environment first.\n", id="question-setup"
        ),
        pytest.param("Here's what pip does when a wheel is unavailable: it builds from source.\n", id="heres-what"),
        pytest.param(
            "A wheel avoids not only compiling the extension but also installing a compiler.\n", id="not-only-but-also"
        ),
        pytest.param("Call insert_rows after the INSERT statement.\n", id="snake-case-insert"),
        pytest.param("The build failed due to the fact that the cache was stale.\n", id="concision"),
    ],
)
def test_text_does_not_trigger_gate(text: str) -> None:
    result = _run_score(text)
    assert result.returncode == 0
    assert "GATE  0 findings" in result.stdout


def test_voice_counts_contractions_and_dashes_without_judgment() -> None:
    result = _run_score("I've tested it. You\u2019ll see why\u2014it's broken. Don't stop.\n")
    assert result.returncode == 0
    assert result.stdout.splitlines()[2] == "VOICE  sentence-length CV 0.00  contractions 4  dashes 1"


@pytest.mark.parametrize(
    ("text", "advisory"),
    [
        pytest.param(
            "Type hints document inputs. Libraries can publish type hints. Teams can check type hints during CI.\n",
            "ADVISORY  0 findings  none",
            id="repeated-term",
        ),
        pytest.param(
            "The parser exits when input is missing. The parser exits when the file is empty. "
            "The parser exits when the header is invalid.\n",
            "ADVISORY  1 findings  repeated sentence openers",
            id="repeated-opener",
        ),
        pytest.param(
            "The cache expires after an hour, ensuring fresh reads.\n",
            "ADVISORY  1 findings  participle tails",
            id="participle-tail",
        ),
        pytest.param(
            "The patch moves the parser while preserving the old API.\n",
            "ADVISORY  1 findings  preserving assurance",
            id="preserving-assurance",
        ),
        pytest.param(
            "The build failed due to the fact that the cache was stale.\n",
            "ADVISORY  1 findings  concision",
            id="concision",
        ),
        pytest.param(
            "The parser reads \u201cconfig\u201d first.\n", "ADVISORY  2 findings  curly quotes x2", id="curly-quotes"
        ),
        pytest.param(
            "# Fixing The Parser Cache\n\nThe parser exits on error.\n",
            "ADVISORY  1 findings  title-case headings",
            id="title-case-heading",
        ),
        pytest.param(
            "# Python Packaging\n\nThe parser exits on error.\n", "ADVISORY  0 findings  none", id="proper-noun-heading"
        ),
        pytest.param(
            "# Fixing the parser cache\n\nThe parser exits on error.\n",
            "ADVISORY  0 findings  none",
            id="sentence-case-heading",
        ),
        pytest.param(
            "Alpha reads the file. Beta parses the header. Gamma checks the body. Delta writes the cache. "
            "Epsilon closes the stream.\n",
            "ADVISORY  1 findings  uniform rhythm",
            id="uniform-rhythm",
        ),
        # Models use agentless passive less often than people do, so it is not counted.
        pytest.param("The file was written by the parser.\n", "ADVISORY  0 findings  none", id="passive-voice"),
    ],
)
def test_advisory_findings(text: str, advisory: str) -> None:
    result = _run_score(text)
    assert result.returncode == 0
    assert result.stdout.splitlines()[1] == advisory


def test_gate_summary_truncates_after_fourteen_categories() -> None:
    result = _run_score(
        "As an AI, I agree. Lorem ipsum. More than just a fix. Sit with that. Think about it. It turns out fine. "
        "Plot twist. Full stop. The stakes are high. A pivotal moment. A cutting-edge tool. A deep dive. "
        "The data tells us. At its core. It's about speed. It's about trust.\n"
    )
    assert result.stdout.splitlines()[0].endswith(", (+1 more)")


def test_code_file_reports_findings(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text("class CacheManager:\n    pass\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(_SCRIPT), str(source)], text=True, capture_output=True, check=False)
    assert result.returncode == 0
    assert "CODE  1 findings" in result.stdout
