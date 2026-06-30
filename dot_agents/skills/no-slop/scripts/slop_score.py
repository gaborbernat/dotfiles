#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Score text for AI slop on two tracks: a high-precision GATE and a graded ADVISORY.

Usage: slop_score.py FILE...   |   echo "text" | slop_score.py

GATE lists AI-unambiguous tells that good human prose does not contain (delve,
"not just X but Y", AI self-disclosure, brochure language). Any hit fails the
run. Calibrated against a pre-AI human corpus so genuine technical writing stays
at 100.

ADVISORY is the stricter no-slop style layer plus statistical signals (em dashes,
adverbs, passive voice, weak hedges, chatbot tone, copula avoidance, uniform
rhythm, over-structured markdown). Human writing trips these too, so they never
fail the run; they show what to keep fixing. A clean gate is necessary, never
sufficient: apply every no-slop rule by hand regardless.

Scoring (density per 1000 words, exponential decay, concentration multiplier on
clustered tells), tiers, and word lists are adapted from eric-tramel/slop-guard,
gabelul/slopbuster, and the Kobak/Liang corpus studies.
"""

from __future__ import annotations

import math
import pathlib
import re
import statistics
import sys
from collections import Counter
from typing import Final

_DECAY_LAMBDA: Final[float] = 0.04
_CONCENTRATION_ALPHA: Final[float] = 2.5
_DENSITY_BASIS: Final[float] = 1000.0
_RHYTHM_MIN_SENTENCES: Final[int] = 5
_RHYTHM_CV_THRESHOLD: Final[float] = 0.3
_COLON_PER_WORDS: Final[float] = 150.0
_COLON_THRESHOLD: Final[float] = 1.5
_BULLET_DENSITY_THRESHOLD: Final[float] = 0.40
_MIN_STRUCTURE_LINES: Final[int] = 5
_BLOCKQUOTE_MIN: Final[int] = 3
_HR_MIN: Final[int] = 4
_BOLD_BULLET_RUN_MIN: Final[int] = 3
_NGRAM_MIN: Final[int] = 4
_NGRAM_MAX: Final[int] = 8
_NGRAM_MIN_COUNT: Final[int] = 3
_PITHY_MAX_WORDS: Final[int] = 6
_SHORT_TEXT_WORDS: Final[int] = 10
_MAX_SHOWN: Final[int] = 14

_Spec = tuple[str, int, bool, tuple[str, ...]]
_CompiledSpec = tuple[str, int, bool, re.Pattern[str]]

# Concentrated categories get the slop-guard multiplier so clustered tells drop the score fast.
_GATE: Final[tuple[_Spec, ...]] = (
    (
        "ai-disclosure",
        -10,
        False,
        (
            r"\bas an ai\b",
            r"\bas a (?:large )?language model\b",
            r"\bi'?m (?:just )?an ai\b",
            r"\bas of my (?:last )?(?:training|knowledge|update)\b",
            r"\bup to my last (?:training|update)\b",
            r"\bknowledge cut-?off\b",
            r"\bi don'?t have (?:access to )?real-?time\b",
            r"\bi can'?t provide\b",
            r"\bi'?m unable to (?:browse|access)\b",
        ),
    ),
    (
        "placeholder",
        -5,
        False,
        (
            r"\[insert\b",
            r"\blorem ipsum\b",
            r"\byour name here\b",
            r"\btktk\b",
            r"\[citation needed\]",
            r"\[link\]",
            r"\bxxxx+\b",
        ),
    ),
    (
        "contrast",
        -3,
        True,
        (
            r"\bnot just\b[^.?!]{1,40}\bbut(?: also)?\b",
            r"\bnot only\b[^.?!]{1,40}\bbut(?: also)?\b",
            r"\bit'?s not\b[^.?!]{0,40}\bit'?s\b",
            r"\bit'?s not merely\b[^.?!]{0,40}\bit'?s\b",
            r"\bthe answer isn'?t\b",
            r"\bthe question isn'?t\b",
            r"\bthe problem isn'?t\b",
            r"\bisn'?t the problem\b",
            r"\bnot because\b[^.?!]{0,40}\bbecause\b",
            r"\bgoes beyond\b[^.?!]{0,30}\bto\b",
            r"\bmore than just\b",
        ),
    ),
    (
        "setup-resolution",
        -3,
        True,
        (
            r"\bwhat if\b[^?]{0,60}\?",
            r"\bhere'?s what i mean\b",
            r"\bthink about it\b",
            r"\band that'?s okay\b",
            r"\bhere'?s the thing\b",
        ),
    ),
    ("fragmentation", -3, True, (r"\bthat'?s it\.\s+that'?s the\b", r"\.\s+and \w+\.\s+and \w+\.")),
    (
        "throat-clearing",
        -3,
        False,
        (
            r"\bhere'?s what\b",
            r"\bhere'?s why\b",
            r"\bhere'?s the problem\b",
            r"\bthe uncomfortable truth\b",
            r"\bit turns out\b",
            r"\blet me be clear\b",
            r"\bthe truth is,",
            r"\bi'?ll say it again\b",
            r"\bi'?m going to be honest\b",
            r"\bcan we talk about\b",
        ),
    ),
    (
        "meta",
        -3,
        False,
        (
            r"\bplot twist\b",
            r"\bspoiler:?",
            r"\byou already know this\b",
            r"\ba feature,? not a bug\b",
        ),
    ),
    (
        "emphasis",
        -3,
        False,
        (
            r"\bfull stop\.",
            r"\blet that sink in\b",
            r"\bmake no mistake\b",
            r"\bhere'?s why that matters\b",
        ),
    ),
    (
        "vague-declarative",
        -3,
        False,
        (
            r"\bthe reasons are structural\b",
            r"\bthe implications are significant\b",
            r"\bthe stakes are high\b",
            r"\bthe consequences are real\b",
            r"\bthe deepest problem\b",
            r"\bcannot be overstated\b",
            r"\bprofound implications\b",
        ),
    ),
    (
        "significance-inflation",
        -3,
        False,
        (
            r"\bpivotal moment\b",
            r"\bgame[- ]chang(?:er|ing)\b",
            r"\b(?:key |a )?turning point\b",
            r"\bplays a (?:crucial|pivotal|vital|key|central|critical) role\b",
            r"\b(?:a|is a) testament to\b",
            r"\bstands as a testament\b",
            r"\bin the realm of\b",
            r"\bsetting the stage for\b",
            r"\bindelible mark\b",
            r"\bdeeply rooted\b",
            r"\bfocal point\b",
            r"\bevolving landscape\b",
            r"\b(?:marks|represents) a (?:shift|turning)\b",
            r"\bis a reminder\b",
        ),
    ),
    (
        "brochure",
        -3,
        False,
        (
            r"\bnestled\b",
            r"\bin the heart of\b",
            r"\bstate[- ]of[- ]the[- ]art\b",
            r"\bcutting[- ]edge\b",
            r"\bworld[- ]class\b",
            r"\bunparalleled\b",
            r"\bgroundbreaking\b",
            r"\bbreathtaking\b",
            r"\bmust[- ]visit\b",
            r"\btransformative\b",
            r"\bboasts a\b",
            r"\bvibrant\b",
        ),
    ),
    (
        "jargon",
        -3,
        False,
        (
            r"\bdeep dive\b",
            r"\bdouble down\b",
            r"\bcircle back\b",
            r"\bmove the needle\b",
            r"\blean into\b",
            r"\btake a step back\b",
            r"\bon the same page\b",
            r"\bmoving forward\b",
        ),
    ),
    (
        "false-agency",
        -3,
        False,
        (
            r"\bthe data tells us\b",
            r"\bthe market rewards\b",
            r"\bthe decision emerges\b",
            r"\bthe conversation moves\b",
            r"\bthe culture shifts\b",
            r"\bthe numbers tell\b",
        ),
    ),
    (
        "wordy-filler",
        -3,
        False,
        (
            r"\bat its core\b",
            r"\bin today'?s\b",
            r"\bit'?s worth (?:noting|mentioning)\b",
            r"\bat the end of the day\b",
            r"\bin a world where\b",
            r"\bdue to the fact that\b",
            r"\bat this point in time\b",
            r"\bit is important to note\b",
            r"\bneedless to say\b",
            r"\bit goes without saying\b",
            r"\bas a matter of fact\b",
            r"\bthe fact of the matter\b",
            r"\bfor all intents and purposes\b",
        ),
    ),
    (
        "ai-vocabulary",
        -2,
        False,
        (
            r"\bdelv(?:e|es|ed|ing)\b",
            r"\bshowcas(?:e|es|ed|ing)\b",
            r"\bmultifaceted\b",
            r"\bnuanced\b",
            r"\bmeticulous(?:ly)?\b",
            r"\bcommendable\b",
            r"\bnoteworthy\b",
            r"\btapestry\b",
            r"\bkaleidoscope\b",
            r"\bsymphony\b",
            r"\bcornerstone\b",
            r"\binterplay\b",
            r"\bintricac(?:y|ies)\b",
            r"\bintricate\b",
            r"\bfostering\b",
            r"\bsymboliz(?:e|es|ing)\b",
            r"\blabyrinthine\b",
            r"\bpalpable\b",
            r"\btranscend(?:s|ed|ing)?\b",
            r"\belucidat(?:e|es|ing)\b",
            r"\bever[- ](?:evolving|changing)\b",
        ),
    ),
)

_ADVISORY_WORDS: Final[dict[str, tuple[str, ...]]] = {
    "named adverbs": (
        "really",
        "literally",
        "genuinely",
        "honestly",
        "simply",
        "actually",
        "deeply",
        "truly",
        "fundamentally",
        "inherently",
        "inevitably",
        "interestingly",
        "importantly",
        "crucially",
        "seamlessly",
        "effortlessly",
        "notably",
    ),
    "puff adjectives": (
        "crucial",
        "key",
        "vital",
        "essential",
        "valuable",
        "robust",
        "novel",
        "comprehensive",
        "holistic",
        "pivotal",
        "profound",
        "remarkable",
        "versatile",
        "fascinating",
        "intriguing",
        "compelling",
        "significant",
        "innovative",
    ),
    "vague transitions": ("additionally", "moreover", "furthermore"),
}
# Chatbot pleasantries: strong AI signal but humans use them too, so advisory not gate.
_CHATBOT: Final[re.Pattern[str]] = re.compile(
    r"\b(?:feel free to|don'?t hesitate to|happy to help|of course!|certainly!|great question"
    r"|you'?re absolutely right|is there anything else|let me know if|would you like me to"
    r"|i hope this (?:helps|is helpful)|to my knowledge|based on available information)",
    re.IGNORECASE,
)
# Copula avoidance: inflated linking verb dodging a plain "is". Common enough in human prose to be advisory.
_COPULA: Final[re.Pattern[str]] = re.compile(
    r"\b(?:serves as|acts as|functions as|stands as|operates as|plays host to)\b", re.IGNORECASE
)
_WEASEL: Final[re.Pattern[str]] = re.compile(
    r"\b(?:studies show|research suggests|experts? (?:say|argue)|critics? argue|it is widely believed|"
    r"many (?:argue|believe)|observers have|industry reports|is widely recognized|has been featured in)\b",
    re.IGNORECASE,
)
_GENERIC_TRANSITION: Final[re.Pattern[str]] = re.compile(
    r"(?:^|\.\s+)(?:that said|moving on|with that in mind|in conclusion|in summary|to sum up),?",
    re.IGNORECASE,
)
_ADVERB_STOP: Final[frozenset[str]] = frozenset({
    "only",
    "family",
    "reply",
    "supply",
    "apply",
    "comply",
    "multiply",
    "rely",
    "ally",
    "fully",
    "holy",
    "ugly",
    "early",
    "italy",
    "july",
    "assembly",
    "anomaly",
    "monopoly",
    "panoply",
    "bully",
    "rally",
    "tally",
    "folly",
    "lily",
    "jelly",
    "belly",
    "imply",
    "wholly",
    "likely",
    "lonely",
    "daily",
    "weekly",
    "monthly",
    "yearly",
})
_GATE_COMPILED: Final[tuple[_CompiledSpec, ...]] = tuple(
    (name, penalty, concentrated, re.compile("|".join(patterns), re.IGNORECASE))
    for name, penalty, concentrated, patterns in _GATE
)
_SENT_SPLIT: Final[re.Pattern[str]] = re.compile(r"[.!?]+(?:\s|$)")
_WORD: Final[re.Pattern[str]] = re.compile(r"[a-z][a-z'-]*", re.IGNORECASE)
_PASSIVE: Final[re.Pattern[str]] = re.compile(
    r"""
    \b (?: is | are | was | were | be | been | being | am ) \s+   # be-auxiliary that hides the actor
    (?: \w+ ed                                                    # regular past participle
      | done | made | given | taken | seen | known | written      # common irregulars
      | built | sent | held | kept | left | told | shown
      | found | paid | put | set | born | drawn | grown ) \b
    """,
    re.VERBOSE | re.IGNORECASE,
)
_RULE_OF_THREE: Final[re.Pattern[str]] = re.compile(
    r"""
    \b \w+ , \s+ \w+ ,? \s+ and \s+ \w+ \b   # tricolon: "item, item, and item"
    """,
    re.VERBOSE,
)


def main() -> int:
    failed = False
    for name, text in read_inputs():
        failed = report(name, text) or failed
    if not failed:
        sys.stderr.write("gate passed — it checks a subset only; still apply every no-slop rule by hand\n")
    return 1 if failed else 0


def read_inputs() -> list[tuple[str, str]]:
    if args := sys.argv[1:]:
        return [(name, pathlib.Path(name).read_text(encoding="utf-8")) for name in args]
    return [("<stdin>", sys.stdin.read())]


def report(name: str, text: str) -> bool:
    words = _WORD.findall(text.lower())
    if len(words) < _SHORT_TEXT_WORDS:
        sys.stdout.write(f"GATE  --/100  {name}  (too short)\n")
        return False
    gate_hits, gate_penalty = scan(text, _GATE_COMPILED)
    gate = 100 if not gate_hits else score_from_density(gate_penalty, len(words))
    advisory_hits, advisory_penalty = advisory(text, words)
    advisory_score = score_from_density(advisory_penalty, len(words))
    sys.stdout.write(
        f"GATE  {gate:3d}/100  {name}  {summarize(gate_hits) or 'clean'}\n"
        f"ADVISORY  {advisory_score:3d}/100 ({_band(advisory_score)})  {summarize(advisory_hits) or 'clean'}\n"
    )
    return bool(gate_hits)


def scan(text: str, specs: tuple[_CompiledSpec, ...]) -> tuple[Counter[str], float]:
    hits: Counter[str] = Counter()
    penalty = 0.0
    for name, weight, concentrated, pattern in specs:
        if count := len(pattern.findall(text)):
            hits[name] = count
            penalty += abs(weight) * (_concentrated(count) if concentrated else count)
    return hits, penalty


def advisory(text: str, words: list[str]) -> tuple[Counter[str], float]:
    hits: Counter[str] = Counter()
    penalty = 0.0
    for name, count, weight in _advisory_signals(text, words):
        if count:
            hits[name] = count
            penalty += weight * count
    return hits, penalty


def _advisory_signals(text: str, words: list[str]) -> list[tuple[str, int, int]]:
    lowered = text.lower()
    counts = Counter(words)
    lines = [line for line in text.splitlines() if line.strip()]
    bullets = sum(1 for line in lines if re.match(r"\s*([-*+]|\d+\.)\s", line))
    bold_bullets = sum(1 for line in lines if re.match(r"\s*([-*+]|\d+\.)\s+\*\*", line))
    blockquotes = sum(1 for line in lines if line.lstrip().startswith(">"))
    hrules = sum(1 for line in lines if re.fullmatch(r"\s*([-*_])\1{2,}\s*", line))
    dense_bullets = len(lines) >= _MIN_STRUCTURE_LINES and bullets > _BULLET_DENSITY_THRESHOLD * len(lines)
    return [
        ("named adverbs", sum(counts[word] for word in _ADVISORY_WORDS["named adverbs"]), 2),
        ("puff adjectives", sum(counts[word] for word in _ADVISORY_WORDS["puff adjectives"]), 1),
        ("vague transitions", sum(counts[word] for word in _ADVISORY_WORDS["vague transitions"]), 1),
        ("-ly adverbs", _count_adverbs(words), 1),
        ("chatbot tone", len(_CHATBOT.findall(text)), 2),
        ("copula avoidance", len(_COPULA.findall(text)), 1),
        ("weasel attribution", len(_WEASEL.findall(text)), 2),
        ("generic transitions", len(_GENERIC_TRANSITION.findall(text)), 1),
        ("em dashes", text.count(chr(0x2014)) + text.count(chr(0x2013)), 3),
        ("passive voice", _count_passive(text), 1),
        ("lazy extremes", len(re.findall(r"\b(?:always|never|everyone|everybody|nobody)\b", lowered)), 1),
        ("rule-of-three", len(_RULE_OF_THREE.findall(lowered)), 1),
        ("uniform rhythm", int(_low_rhythm_variance(text)), 5),
        ("colon density", int(_colon_overuse(text, words)), 3),
        ("bullet density", int(dense_bullets), 8),
        ("blockquotes", int(blockquotes >= _BLOCKQUOTE_MIN), 3),
        ("horizontal rules", int(hrules >= _HR_MIN), 3),
        ("bold-bullet run", int(bold_bullets >= _BOLD_BULLET_RUN_MIN), 5),
        ("repeated phrases", _repeated_ngrams(words), 1),
        ("pithy fragments", _pithy_fragments(text), 2),
    ]


def _count_adverbs(words: list[str]) -> int:
    named = set(_ADVISORY_WORDS["named adverbs"])
    return sum(
        1 for word in words if word.endswith("ly") and len(word) > 4 and word not in _ADVERB_STOP and word not in named
    )


def _count_passive(text: str) -> int:
    return len(_PASSIVE.findall(text))


def _low_rhythm_variance(text: str) -> bool:
    lengths = [count for part in _SENT_SPLIT.split(text) if (count := len(_WORD.findall(part)))]
    if len(lengths) < _RHYTHM_MIN_SENTENCES:
        return False
    mean = statistics.fmean(lengths)
    return statistics.pstdev(lengths) / mean < _RHYTHM_CV_THRESHOLD


def _colon_overuse(text: str, words: list[str]) -> bool:
    colons = len(re.findall(r"[a-z]:\s", text, re.IGNORECASE))
    return colons / (len(words) / _COLON_PER_WORDS) > _COLON_THRESHOLD


def _repeated_ngrams(words: list[str]) -> int:
    repeated: set[str] = set()
    for size in range(_NGRAM_MIN, _NGRAM_MAX + 1):
        grams = Counter(" ".join(words[index : index + size]) for index in range(len(words) - size + 1))
        repeated |= {gram for gram, count in grams.items() if count >= _NGRAM_MIN_COUNT}
    return len(repeated)


def _pithy_fragments(text: str) -> int:
    return sum(
        1 for part in _SENT_SPLIT.split(text) if "," in part and 0 < len(_WORD.findall(part)) <= _PITHY_MAX_WORDS
    )


def _concentrated(count: int) -> float:
    return 1.0 + _CONCENTRATION_ALPHA * (count - 1)


def score_from_density(penalty: float, word_count: int) -> int:
    density = penalty / (word_count / _DENSITY_BASIS)
    return max(0, min(100, round(100 * math.exp(-_DECAY_LAMBDA * density))))


def _band(score: int) -> str:
    if score >= 80:
        return "clean"
    if score >= 60:
        return "light"
    if score >= 40:
        return "moderate"
    return "heavy"


def summarize(hits: Counter[str]) -> str:
    parts = [name if count == 1 else f"{name} x{count}" for name, count in hits.most_common(_MAX_SHOWN)]
    if (extra := len(hits) - _MAX_SHOWN) > 0:
        parts.append(f"(+{extra} more)")
    return ", ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
