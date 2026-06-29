#!/usr/bin/env python3
"""Score text 0-100 for AI-slop density. Self-contained, stdlib only.

Usage: slop_score.py FILE...   |   echo "text" | slop_score.py
Exit 1 if any input scores below THRESHOLD, so it can gate delivery.
"""

from __future__ import annotations

import pathlib
import re
import sys
from typing import Final

THRESHOLD: Final[int] = 100

_WORDS: Final[frozenset[str]] = frozenset({
    "delve", "delves", "delving", "showcasing", "underscores", "intricate", "multifaceted", "nuanced",
    "meticulous", "meticulously", "commendable", "noteworthy", "remarkable", "tapestry", "testament", "realm",
    "kaleidoscope", "symphony", "beacon", "cornerstone", "versatile", "profound", "fascinating", "intriguing",
    "ingenious", "captivating", "really", "just", "literally", "genuinely", "honestly", "simply", "actually",
    "deeply", "truly", "fundamentally", "inherently", "inevitably", "interestingly", "importantly", "crucially",
})  # fmt: skip

_PHRASES: Final[tuple[str, ...]] = (
    "plays a crucial role",
    "plays a pivotal role",
    "plays a vital role",
    "pivotal moment",
    "navigating the landscape",
    "a testament to",
    "stands as a testament",
    "rich tapestry",
    "a tapestry of",
    "in the realm of",
    "serves as",
    "acts as",
    "it's not",
    "isn't the problem",
    "the answer isn't",
    "here's the thing",
    "here's what",
    "it's worth noting",
    "at its core",
    "in today's",
    "at the end of the day",
    "when it comes to",
    "in a world where",
    "let that sink in",
    "make no mistake",
    "deep dive",
    "game-changer",
)


def score(text: str) -> tuple[int, list[str]]:
    lowered = text.lower()
    tokens = re.findall(r"[a-z']+", lowered)
    if not tokens:
        return 100, []
    hits = [word for word in tokens if word in _WORDS]
    hits += [phrase for phrase in _PHRASES if phrase in lowered]
    if "—" in text:
        hits.append("em-dash")
    if lowered.count(" is ") > max(3, len(tokens) // 80):
        hits.append("copula-chain")
    density = len(hits) / (len(tokens) / 100)
    return max(0, round(100 - 12 * density)), sorted(set(hits))


def main() -> int:
    if args := sys.argv[1:]:
        inputs = [(name, pathlib.Path(name).read_text(encoding="utf-8")) for name in args]
    else:
        inputs = [("<stdin>", sys.stdin.read())]
    worst = 100
    for name, text in inputs:
        value, hits = score(text)
        worst = min(worst, value)
        sys.stdout.write(f"{value:3d}/100  {name}  {', '.join(hits[:20]) or 'clean'}\n")
    if worst == 100:
        sys.stderr.write("gate passed — it checks a subset only; still apply every no-slop rule by hand\n")
    return 0 if worst >= THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
