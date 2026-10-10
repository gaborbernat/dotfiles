from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

SCRIPT: Final[Path] = Path(__file__).parents[1] / "scripts" / "slop_score.py"


def run_score(text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT)], input=text, text=True, capture_output=True, check=False)


@pytest.mark.parametrize(
    ("text", "category", "column"),
    [
        ("This matters because the cache is slow.\n", "emphasis", 1),
        ("The cache finished, highlighting the importance of retries.\n", "participle-tail", 19),
        ("Let me walk you through the cache.\n", "setup-resolution", 1),
        ("It's about speed. It's about trust.\n", "anaphora", 1),
    ],
)
def test_gate_reports_location(text: str, category: str, column: int) -> None:
    result = run_score("The parser exits on error.\n" + text)
    assert result.returncode == 1
    assert f"<stdin>:2:{column}: {category}:" in result.stdout


def test_markdown_code_does_not_trigger_gate() -> None:
    result = run_score("Use `this matters because` as input.\n```python\nprint('this matters because')\n```\n")
    assert result.returncode == 0
    assert "GATE  0 findings" in result.stdout


def test_gate_reports_location_after_tilde_fence() -> None:
    result = run_score("~~~python\nprint('this matters because')\n~~~~\nThis matters because retries can loop.\n")
    assert result.returncode == 1
    assert "<stdin>:4:1: emphasis:" in result.stdout


@pytest.mark.parametrize("word", ["nuanced", "transformative"])
def test_stock_word_is_advisory(word: str) -> None:
    result = run_score(f"The analysis is {word}.\n")
    assert result.returncode == 0
    assert "stock vocabulary" in result.stdout


def test_literal_list_does_not_trigger_gate() -> None:
    result = run_score("Run the parser, renderer, and formatter.\n")
    assert result.returncode == 0


@pytest.mark.parametrize(
    "text",
    [
        "What if pip has to build from source? It creates an isolated environment first.\n",
        "Here's what pip does when a wheel is unavailable: it builds from source.\n",
        "A wheel avoids not only compiling the extension but also installing a compiler.\n",
    ],
)
def test_technical_explanation_does_not_trigger_gate(text: str) -> None:
    result = run_score(text)
    assert result.returncode == 0
    assert "GATE  0 findings" in result.stdout


def test_voice_counts_contractions_and_dashes_without_judgment() -> None:
    result = run_score("I've tested it. You\u2019ll see why\u2014it's broken. Don't stop.\n")
    assert result.returncode == 0
    assert "VOICE  sentence-length CV" in result.stdout
    assert "contractions 4  dashes 1" in result.stdout
    assert "off profile" not in result.stdout


def test_repeated_technical_term_is_not_repeated_opener() -> None:
    result = run_score(
        "Type hints document inputs. Libraries can publish type hints. Teams can check type hints during CI.\n"
    )
    assert result.returncode == 0
    assert "repeated sentence openers" not in result.stdout


def test_repeated_sentence_opener_is_advisory() -> None:
    result = run_score(
        "The parser exits when input is missing. The parser exits when the file is empty. "
        "The parser exits when the header is invalid.\n"
    )
    assert result.returncode == 0
    assert "repeated sentence openers" in result.stdout


def test_code_file_reports_findings(tmp_path: Path) -> None:
    source = tmp_path / "example.py"
    source.write_text("class CacheManager:\n    pass\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(SCRIPT), str(source)], text=True, capture_output=True, check=False)
    assert result.returncode == 0
    assert "CODE  1 findings" in result.stdout
