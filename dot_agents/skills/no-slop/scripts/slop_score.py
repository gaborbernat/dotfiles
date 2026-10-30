#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Find formulaic prose for review against a local writing style."""

from __future__ import annotations

import operator
import pathlib
import re
import statistics
import sys
from collections import Counter
from typing import Final

_APOS: Final[str] = r"['\u2019]"
_TOTALIZING_NOUNS: Final[str] = r"(?:point|game|thing|idea|premise|argument|joke|trick|business model)"

_CompiledSpec = tuple[str, re.Pattern[str]]

_GATE: Final[tuple[_CompiledSpec, ...]] = tuple(
    (name, re.compile("|".join(patterns), re.IGNORECASE))
    for name, patterns in (
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
_WORD: Final[re.Pattern[str]] = re.compile(r"[a-z][a-z'-]*", re.IGNORECASE)
_SENT_SPLIT: Final[re.Pattern[str]] = re.compile(r"[.!?]+(?:\s|$)")


def main() -> int:
    failed = False
    for name, text in _read_inputs():
        failed = _report(name, text) or failed
    sys.stderr.write(
        "\nReview findings in context, then check facts, task fit, and voice by hand.\n"
        "A match is not evidence of AI authorship; zero findings do not establish quality.\n"
    )
    return 1 if failed else 0


def _read_inputs() -> list[tuple[str, str]]:
    if args := sys.argv[1:]:
        return [(name, pathlib.Path(name).read_text(encoding="utf-8")) for name in args]
    return [("<stdin>", sys.stdin.read())]


def _report(name: str, text: str) -> bool:
    if pathlib.Path(name).suffix in {
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
    }:
        _code_report(name, text)
        return False
    prose = _prose_only(text)
    gate_hits = _scan(prose, _GATE)
    advisory_hits = _advisory(prose)
    sys.stdout.write(
        f"GATE  {sum(gate_hits.values())} findings  {name}  {_summarize(gate_hits) or 'none'}\n"
        f"ADVISORY  {sum(advisory_hits.values())} findings  {_summarize(advisory_hits) or 'none'}\n"
        f"{_voice_line(prose)}\n"
    )
    for category, line, column, match in _gate_locations(prose, text):
        sys.stdout.write(f"  {name}:{line}:{column}: {category}: {match!r}\n")
    return bool(gate_hits)


def _code_report(name: str, text: str) -> None:
    hits = _scan(
        text,
        (
            ("section-banner comment", re.compile(r"(?m)^[ \t]*(?:#|//)[ \t]*[-=*~_]{3,}")),
            (
                "narrator comment",
                re.compile(r"(?im)^[ \t]*(?:#|//)[ \t]*(?:now we\b|we [a-z]|let'?s\b|first,? we\b|next,? we\b)"),
            ),
            ("filler-noun class", re.compile(r"\bclass\s+[A-Za-z0-9_]+(?:Manager|Helper|Utils?|Wrapper|Processor)\b")),
            (
                "tautological docstring",
                re.compile(r'(?i)"""\s*(?:returns?|gets?|sets?|runs?|creates?|does?|handles?)\.?\s*"""'),
            ),
        ),
    )
    sys.stdout.write(f"CODE  {sum(hits.values())} findings  {name}  {_summarize(hits) or 'none'}\n")


def _scan(text: str, specs: tuple[_CompiledSpec, ...]) -> Counter[str]:
    hits: Counter[str] = Counter()
    for name, pattern in specs:
        if count := len(pattern.findall(text)):
            hits[name] = count
    return hits


def _summarize(hits: Counter[str]) -> str:
    shown = 14
    parts = [name if count == 1 else f"{name} x{count}" for name, count in hits.most_common(shown)]
    if (extra := len(hits) - shown) > 0:
        parts.append(f"(+{extra} more)")
    return ", ".join(parts)


def _prose_only(text: str) -> str:
    lines: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence is None and marker:
            token = marker.group(1)
            fence = (token[0], len(token))
        elif fence and marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= fence[1]:
            if not marker.group(2).strip():
                fence = None
        elif fence is None:
            lines.append(re.sub(r"(`+)(?!`)[^`\n]*?\1(?!`)", lambda match: " " * len(match.group()), line))
            continue
        lines.append("".join("\n" if character == "\n" else " " for character in line))
    return "".join(lines)


def _advisory(text: str) -> Counter[str]:
    lowered = text.lower()
    words = _WORD.findall(lowered)
    counts = Counter(words)
    lines = [line for line in text.splitlines() if line.strip()]
    bullets = sum(1 for line in lines if re.match(r"\s*([-*+]|\d+\.)\s", line))
    passive = r"""
        \b (?: is | are | was | were | be | been | being | am ) \s+
        (?: \w+ ed
          | done | made | given | taken | seen | known | written
          | built | sent | held | kept | left | told | shown
          | found | paid | put | set | born | drawn | grown ) \b
    """
    signals = {
        **{group: sum(counts[word] for word in members) for group, members in _ADVISORY_WORDS.items()},
        "stock vocabulary": len(
            re.findall(
                r"\b(?:delv(?:e|es|ed|ing)|showcas(?:e|es|ed|ing)|multifaceted|nuanced|meticulous(?:ly)?|commendable"
                r"|noteworthy|tapestry|kaleidoscope|symphony|cornerstone|interplay|intricac(?:y|ies)|intricate"
                r"|fostering|symboliz(?:e|es|ing)|labyrinthine|palpable|transcend(?:s|ed|ing)?"
                r"|elucidat(?:e|es|ing)|ever[- ](?:evolving|changing)|nestled|unparalleled|groundbreaking"
                r"|breathtaking|vibrant|transformative)\b",
                text,
                re.IGNORECASE,
            )
        ),
        "-ly adverbs": _count_adverbs(words),
        # Human writing can use these phrases too.
        "chatbot tone": len(
            re.findall(
                r"\b(?:feel free to|don'?t hesitate to|happy to help|of course!|certainly!|great question"
                r"|you'?re absolutely right|is there anything else|let me know if|would you like me to"
                r"|i hope this (?:helps|is helpful)|to my knowledge|based on available information)",
                text,
                re.IGNORECASE,
            )
        ),
        # An inflated linking verb dodging a plain "is"; common enough in human prose to stay advisory.
        "copula avoidance": len(
            re.findall(
                r"\b(?:serves as|acts as|functions as|stands as|operates as|plays host to)\b", text, re.IGNORECASE
            )
        ),
        "weasel attribution": len(
            re.findall(
                r"\b(?:studies show|research suggests|experts? (?:say|argue)|critics? argue|it is widely believed|"
                r"many (?:argue|believe)|observers have|industry reports|is widely recognized|has been featured in)\b",
                text,
                re.IGNORECASE,
            )
        ),
        "generic transitions": len(
            re.findall(
                r"(?:^|\.\s+)(?:that said|moving on|with that in mind|in conclusion|in summary|to sum up),?",
                text,
                re.IGNORECASE,
            )
        ),
        "passive voice": len(re.findall(passive, text, re.VERBOSE | re.IGNORECASE)),
        "lazy extremes": len(re.findall(r"\b(?:always|never|everyone|everybody|nobody)\b", lowered)),
        "repeated three-item lists": int(len(re.findall(r"\b\w+,\s+\w+,?\s+and\s+\w+\b", lowered)) >= 3),
        "uniform rhythm": int((cv := _sentence_length_cv(text)) is not None and cv < 0.3),
        "colon density": int(_colon_overuse(text, words)),
        "bullet density": int(len(lines) >= 5 and bullets > 0.40 * len(lines)),
        "blockquotes": int(sum(1 for line in lines if line.lstrip().startswith(">")) >= 3),
        "horizontal rules": int(sum(1 for line in lines if re.fullmatch(r"\s*([-*_])\1{2,}\s*", line)) >= 4),
        "bold-bullet run": int(sum(1 for line in lines if re.match(r"\s*([-*+]|\d+\.)\s+\*\*", line)) >= 3),
        "repeated sentence openers": _repeated_openers(text),
        "pithy fragments": _pithy_fragments(text),
    }
    return Counter({name: count for name, count in signals.items() if count})


def _count_adverbs(words: list[str]) -> int:
    skip = {
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
        *_ADVISORY_WORDS["named adverbs"],
    }
    return sum(1 for word in words if word.endswith("ly") and len(word) > 4 and word not in skip)


def _sentence_length_cv(text: str) -> float | None:
    if len(lengths := [count for part in _SENT_SPLIT.split(text) if (count := len(_WORD.findall(part)))]) < 5:
        return None
    return statistics.pstdev(lengths) / statistics.fmean(lengths)


def _colon_overuse(text: str, words: list[str]) -> bool:
    return bool(words) and len(re.findall(r"[a-z]:\s", text, re.IGNORECASE)) / (len(words) / 150.0) > 1.5


def _repeated_openers(text: str) -> int:
    opener_words = 4
    openers = Counter(
        tuple(words[:opener_words])
        for part in _SENT_SPLIT.split(text)
        if len(words := _WORD.findall(part.lower())) >= opener_words
    )
    return sum(count >= 3 for count in openers.values())


def _pithy_fragments(text: str) -> int:
    return sum(1 for part in _SENT_SPLIT.split(text) if "," in part and 0 < len(_WORD.findall(part)) <= 6)


def _voice_line(text: str) -> str:
    contraction = rf"\b[a-z]+{_APOS}(?:t|re|ve|ll|d|m)\b|\b(?:it|that|there|what|who|where|how|let|she|he){_APOS}s\b"
    return (
        f"VOICE  sentence-length CV {_sentence_length_cv(text) or 0.0:.2f}"
        f"  contractions {len(re.findall(contraction, text, re.IGNORECASE))}"
        f"  dashes {text.count(chr(0x2014)) + text.count(chr(0x2013))}"
    )


def _gate_locations(prose: str, original: str) -> list[tuple[str, int, int, str]]:
    locations: list[tuple[str, int, int, str]] = []
    for category, pattern in _GATE:
        for match in pattern.finditer(prose):
            start = match.start()
            line = original.count("\n", 0, start) + 1
            column = start - original.rfind("\n", 0, start)
            locations.append((category, line, column, original[start : match.end()].replace("\n", " ")))
    return sorted(locations, key=operator.itemgetter(1, 2))


if __name__ == "__main__":
    raise SystemExit(main())
