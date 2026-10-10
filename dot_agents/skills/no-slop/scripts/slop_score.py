#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Find formulaic prose for review against a local writing style.

Usage: slop_score.py FILE...   |   echo "text" | slop_score.py

GATE marks stock phrases and placeholders to edit before delivery. A hit says
nothing about authorship. Markdown code spans and fences are excluded.

ADVISORY reports broader style signals (adverbs, passive voice, rhythm, and
formatting). Human writing trips these too; review them in context. VOICE shows
descriptive counts, not whether writing matches an author's voice.

Findings are local edit aids, not calibrated probabilities or AI detectors.
"""

from __future__ import annotations

import operator
import pathlib
import re
import statistics
import sys
from collections import Counter
from typing import Final

_RHYTHM_MIN_SENTENCES: Final[int] = 5
_RHYTHM_CV_THRESHOLD: Final[float] = 0.3
_COLON_PER_WORDS: Final[float] = 150.0
_COLON_THRESHOLD: Final[float] = 1.5
_BULLET_DENSITY_THRESHOLD: Final[float] = 0.40
_MIN_STRUCTURE_LINES: Final[int] = 5
_BLOCKQUOTE_MIN: Final[int] = 3
_HR_MIN: Final[int] = 4
_BOLD_BULLET_RUN_MIN: Final[int] = 3
_OPENER_WORDS: Final[int] = 4
_OPENER_MIN_COUNT: Final[int] = 3
_TRICOLON_MIN_COUNT: Final[int] = 3
_PITHY_MAX_WORDS: Final[int] = 6
_MAX_SHOWN: Final[int] = 14
_REMINDER: Final[str] = (
    "\nReview findings in context, then check facts, task fit, and voice by hand.\n"
    "A match is not evidence of AI authorship; zero findings do not establish quality.\n"
)

_APOS: Final[str] = r"['\u2019]"
_TOTALIZING_NOUNS: Final[str] = r"(?:point|game|thing|idea|premise|argument|joke|trick|business model)"

_Spec = tuple[str, tuple[str, ...]]
_CompiledSpec = tuple[str, re.Pattern[str]]

_GATE: Final[tuple[_Spec, ...]] = (
    (
        "ai-disclosure",
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
        (
            r"\bit'?s not\b[^.?!]{0,40}\bit'?s\b",
            r"\bit'?s not merely\b[^.?!]{0,40}\bit'?s\b",
            r"\bthe answer isn'?t\b",
            r"\bthe question isn'?t\b",
            r"\bthe problem isn'?t\b",
            r"\bisn'?t the problem\b",
            r"\bnot because\b[^.?!]{0,40}\bbecause\b",
            r"\bit'?s not\b[^.!?\n]{1,50}\.\s+it'?s\b",
            r"\bgoes beyond\b[^.?!]{0,30}\bto\b",
            r"\bmore than just\b",
            # "Don't call it X. Call it Y." - same verb negated, then repeated.
            (
                r"\b(?:do not|don'?t) (?:just |simply |merely )?(\w+) it\b[^.!?\n]{0,60}[.!?;,:]\s*"
                r"(?:just |simply )?\1 it\b"
            ),
            r"\bno \w+, no \w+, no \w+",
            (
                r"\b(?:did not|didn'?t) \w+[^.?!\n]{0,40}, (?:did not|didn'?t) \w+[^.?!\n]{0,40}, "
                r"(?:did not|didn'?t)\b"
            ),
            r"\bit wasn'?t\b[^.!?\n]{1,50}\.\s+it wasn'?t\b[^.!?\n]{1,50}\.\s+it was\b",
        ),
    ),
    (
        "therapist",
        (
            r"\bsit(?:s|ting)? with (?:that|this|it)\b",
            (
                r"\bsit(?:s|ting)? with (?:the|your) (?:discomfort|feelings?|tension|weight|uncertainty"
                r"|ambiguity|grief|silence|unease)\b"
            ),
            rf"\b(?:that|this|it|which)(?:{_APOS}s| is| was) not nothing\b",
            r"\b(?:is|are|was|were|feels?|seems?)(?: \w+){0,2}? worth naming\b",
            r"\bworth naming:",
            r"\bis real,? (?:and|but|not)\b",
            # Bare wh-words stay out: "you already know how to run the tests" is ordinary writing.
            r"\byou already know (?:the answer|what to do)\b",
            r"\byou already know\b(?![ \t]+\w)",
        ),
    ),
    (
        "setup-resolution",
        (
            r"\bhere'?s what i mean\b",
            r"\bthink about it\b",
            r"\band that'?s (?:okay|allowed|fine)\b",
            r"\bhere'?s the thing\b",
            r"\blet me walk you through\b",
            r"\bthis unlocks something\b",
        ),
    ),
    (
        "fragmentation",
        (r"\bthat'?s it\.\s+that'?s the\b", r"\.\s+and \w+\.\s+and \w+\.", r"\bnot always\.\s+not perfectly\."),
    ),
    (
        "throat-clearing",
        (
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
        (
            r"\bplot twist\b",
            r"\bspoiler:?",
            r"\byou already know this\b",
            r"\ba feature,? not a bug\b",
            r"\bthe rest of this (?:essay|post|article) (?:explains|shows|covers)\b",
        ),
    ),
    (
        "emphasis",
        (
            r"\bfull stop\.",
            r"\blet that sink in\b",
            r"\bmake no mistake\b",
            r"\bhere'?s why that matters\b",
            r"\bthis matters because\b",
        ),
    ),
    (
        "vague-declarative",
        (
            r"\bthe reasons are structural\b",
            r"\bthe implications are significant\b",
            r"\bthe stakes are high\b",
            r"\bthe consequences are real\b",
            r"\bthe deepest problem\b",
            r"\bcannot be overstated\b",
            r"\bprofound implications\b",
            r"\bthis is what \w+(?: \w+){0,3} actually looks like\b",
            r"\bthe future belongs to\b",
        ),
    ),
    (
        "significance-inflation",
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
            # Totalizing closers. The noun list keeps "the entire system is down" out.
            rf"\b(?:that|this)(?:{_APOS}s| is| was) the whole {_TOTALIZING_NOUNS}\b",
            rf"(?:\bis|\bwas|\bare|\bwere|{_APOS}s) the entire {_TOTALIZING_NOUNS}\b",
            rf"\bthe entire {_TOTALIZING_NOUNS}(?: \w+){{0,3}}? (?:is|was)\b",
            r"\bthe punchline(?: (?:is|was)\b|\s*[:?])",
        ),
    ),
    (
        "brochure",
        (
            r"\bin the heart of\b",
            r"\bstate[- ]of[- ]the[- ]art\b",
            r"\bcutting[- ]edge\b",
            r"\bworld[- ]class\b",
            r"\bmust[- ]visit\b",
            r"\bboasts a\b",
        ),
    ),
    (
        "jargon",
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
        "participle-tail",
        (r",\s+(?:underscoring|highlighting|showcasing) (?:the|a) (?:importance|value|need|significance) of\b",),
    ),
    ("anaphora", (r"\bit'?s about\b[^.!?\n]{1,60}\.\s+it'?s about\b",)),
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
_WORD_TELLS: Final[re.Pattern[str]] = re.compile(
    r"\b(?:delv(?:e|es|ed|ing)|showcas(?:e|es|ed|ing)|multifaceted|nuanced|meticulous(?:ly)?|commendable"
    r"|noteworthy|tapestry|kaleidoscope|symphony|cornerstone|interplay|intricac(?:y|ies)|intricate"
    r"|fostering|symboliz(?:e|es|ing)|labyrinthine|palpable|transcend(?:s|ed|ing)?"
    r"|elucidat(?:e|es|ing)|ever[- ](?:evolving|changing)|nestled|unparalleled|groundbreaking"
    r"|breathtaking|vibrant|transformative)\b",
    re.IGNORECASE,
)
# Human writing can use these phrases too.
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
    (name, re.compile("|".join(patterns), re.IGNORECASE)) for name, patterns in _GATE
)
_FENCE: Final[re.Pattern[str]] = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_INLINE_CODE: Final[re.Pattern[str]] = re.compile(r"(`+)(?!`)[^`\n]*?\1(?!`)")
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
_CONTRACTION: Final[re.Pattern[str]] = re.compile(
    r"\b[a-z]+"
    + _APOS
    + r"(?:t|re|ve|ll|d|m)\b"
    + r"|\b(?:it|that|there|what|who|where|how|let|she|he)"
    + _APOS
    + r"s\b",
    re.IGNORECASE,
)
_CODE_EXTS: Final[frozenset[str]] = frozenset({
    ".py",
    ".pyi",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
})
_CODE: Final[tuple[tuple[str, str], ...]] = (
    ("section-banner comment", r"(?m)^[ \t]*(?:#|//)[ \t]*[-=*~_]{3,}"),
    ("narrator comment", r"(?im)^[ \t]*(?:#|//)[ \t]*(?:now we\b|we [a-z]|let'?s\b|first,? we\b|next,? we\b)"),
    ("filler-noun class", r"\bclass\s+[A-Za-z0-9_]+(?:Manager|Helper|Utils?|Wrapper|Processor)\b"),
    ("tautological docstring", r'(?i)"""\s*(?:returns?|gets?|sets?|runs?|creates?|does?|handles?)\.?\s*"""'),
)
_CODE_COMPILED: Final[tuple[tuple[str, re.Pattern[str]], ...]] = tuple(
    (name, re.compile(pattern)) for name, pattern in _CODE
)


def main() -> int:
    failed = False
    for name, text in read_inputs():
        failed = report(name, text) or failed
    sys.stderr.write(_REMINDER)
    return 1 if failed else 0


def read_inputs() -> list[tuple[str, str]]:
    if args := sys.argv[1:]:
        return [(name, pathlib.Path(name).read_text(encoding="utf-8")) for name in args]
    return [("<stdin>", sys.stdin.read())]


def report(name: str, text: str) -> bool:
    if pathlib.Path(name).suffix in _CODE_EXTS:
        return code_report(name, text)
    prose = prose_only(text)
    words = _WORD.findall(prose.lower())
    gate_hits = scan(prose, _GATE_COMPILED)
    advisory_hits = advisory(prose, words)
    sys.stdout.write(
        f"GATE  {sum(gate_hits.values())} findings  {name}  {summarize(gate_hits) or 'none'}\n"
        f"ADVISORY  {sum(advisory_hits.values())} findings  {summarize(advisory_hits) or 'none'}\n"
        f"{_voice_line(prose)}\n"
    )
    for category, line, column, match in gate_locations(prose, text):
        sys.stdout.write(f"  {name}:{line}:{column}: {category}: {match!r}\n")
    return bool(gate_hits)


def prose_only(text: str) -> str:
    lines: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines(keepends=True):
        marker = _FENCE.match(line)
        if fence is None and marker:
            token = marker.group(1)
            fence = (token[0], len(token))
        elif fence and marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= fence[1]:
            if not marker.group(2).strip():
                fence = None
        elif fence is None:
            lines.append(_INLINE_CODE.sub(lambda match: " " * len(match.group()), line))
            continue
        lines.append("".join("\n" if character == "\n" else " " for character in line))
    return "".join(lines)


def gate_locations(prose: str, original: str) -> list[tuple[str, int, int, str]]:
    locations: list[tuple[str, int, int, str]] = []
    for category, pattern in _GATE_COMPILED:
        for match in pattern.finditer(prose):
            start = match.start()
            line = original.count("\n", 0, start) + 1
            column = start - original.rfind("\n", 0, start)
            locations.append((category, line, column, original[start : match.end()].replace("\n", " ")))
    return sorted(locations, key=operator.itemgetter(1, 2))


def code_report(name: str, text: str) -> bool:
    hits: Counter[str] = Counter()
    for category, pattern in _CODE_COMPILED:
        if count := len(pattern.findall(text)):
            hits[category] = count
    sys.stdout.write(f"CODE  {sum(hits.values())} findings  {name}  {summarize(hits) or 'none'}\n")
    return False


def _voice_line(text: str) -> str:
    lengths = [count for part in _SENT_SPLIT.split(text) if (count := len(_WORD.findall(part)))]
    cv = statistics.pstdev(lengths) / statistics.fmean(lengths) if len(lengths) >= _RHYTHM_MIN_SENTENCES else 0.0
    contractions = len(_CONTRACTION.findall(text))
    dashes = text.count(chr(0x2014)) + text.count(chr(0x2013))
    return f"VOICE  sentence-length CV {cv:.2f}  contractions {contractions}  dashes {dashes}"


def scan(text: str, specs: tuple[_CompiledSpec, ...]) -> Counter[str]:
    hits: Counter[str] = Counter()
    for name, pattern in specs:
        if count := len(pattern.findall(text)):
            hits[name] = count
    return hits


def advisory(text: str, words: list[str]) -> Counter[str]:
    hits: Counter[str] = Counter()
    for name, count in _advisory_signals(text, words):
        if count:
            hits[name] = count
    return hits


def _advisory_signals(text: str, words: list[str]) -> list[tuple[str, int]]:
    lowered = text.lower()
    counts = Counter(words)
    lines = [line for line in text.splitlines() if line.strip()]
    bullets = sum(1 for line in lines if re.match(r"\s*([-*+]|\d+\.)\s", line))
    bold_bullets = sum(1 for line in lines if re.match(r"\s*([-*+]|\d+\.)\s+\*\*", line))
    blockquotes = sum(1 for line in lines if line.lstrip().startswith(">"))
    hrules = sum(1 for line in lines if re.fullmatch(r"\s*([-*_])\1{2,}\s*", line))
    dense_bullets = len(lines) >= _MIN_STRUCTURE_LINES and bullets > _BULLET_DENSITY_THRESHOLD * len(lines)
    return [
        ("named adverbs", sum(counts[word] for word in _ADVISORY_WORDS["named adverbs"])),
        ("puff adjectives", sum(counts[word] for word in _ADVISORY_WORDS["puff adjectives"])),
        ("vague transitions", sum(counts[word] for word in _ADVISORY_WORDS["vague transitions"])),
        ("stock vocabulary", len(_WORD_TELLS.findall(text))),
        ("-ly adverbs", _count_adverbs(words)),
        ("chatbot tone", len(_CHATBOT.findall(text))),
        ("copula avoidance", len(_COPULA.findall(text))),
        ("weasel attribution", len(_WEASEL.findall(text))),
        ("generic transitions", len(_GENERIC_TRANSITION.findall(text))),
        ("passive voice", _count_passive(text)),
        ("lazy extremes", len(re.findall(r"\b(?:always|never|everyone|everybody|nobody)\b", lowered))),
        ("repeated three-item lists", int(len(_RULE_OF_THREE.findall(lowered)) >= _TRICOLON_MIN_COUNT)),
        ("uniform rhythm", int(_low_rhythm_variance(text))),
        ("colon density", int(_colon_overuse(text, words))),
        ("bullet density", int(dense_bullets)),
        ("blockquotes", int(blockquotes >= _BLOCKQUOTE_MIN)),
        ("horizontal rules", int(hrules >= _HR_MIN)),
        ("bold-bullet run", int(bold_bullets >= _BOLD_BULLET_RUN_MIN)),
        ("repeated sentence openers", _repeated_openers(text)),
        ("pithy fragments", _pithy_fragments(text)),
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
    if not words:
        return False
    colons = len(re.findall(r"[a-z]:\s", text, re.IGNORECASE))
    return colons / (len(words) / _COLON_PER_WORDS) > _COLON_THRESHOLD


def _repeated_openers(text: str) -> int:
    openers = Counter(
        tuple(words[:_OPENER_WORDS])
        for part in _SENT_SPLIT.split(text)
        if len(words := _WORD.findall(part.lower())) >= _OPENER_WORDS
    )
    return sum(count >= _OPENER_MIN_COUNT for count in openers.values())


def _pithy_fragments(text: str) -> int:
    return sum(
        1 for part in _SENT_SPLIT.split(text) if "," in part and 0 < len(_WORD.findall(part)) <= _PITHY_MAX_WORDS
    )


def summarize(hits: Counter[str]) -> str:
    parts = [name if count == 1 else f"{name} x{count}" for name, count in hits.most_common(_MAX_SHOWN)]
    if (extra := len(hits) - _MAX_SHOWN) > 0:
        parts.append(f"(+{extra} more)")
    return ", ".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
