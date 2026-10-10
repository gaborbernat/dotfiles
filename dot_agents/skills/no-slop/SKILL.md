---
name: no-slop
description: Edit formulaic prose in PRs, commits, comments, docs, and other writing. Use to cut stock phrasing and empty claims while preserving facts, intent, and the author's voice.
---

Edit the draft, then check what the edit changed. The goal is useful prose in the author's voice.

Use [references/phrases.md](references/phrases.md), [references/lexicon.md](references/lexicon.md), and
[references/structures.md](references/structures.md) to identify candidates for revision. A match is a prompt to read
the sentence in context. Keep a phrase when it carries a needed distinction, a quotation, a domain term, or the author's
deliberate style.

1. Check the task, audience, and any length or format constraint. Lead PRs and short replies with the answer or concrete
   change; a longer explanation can open with the technical question it will answer.
1. Cut throat-clearing, repeated framing, empty emphasis, and claims that lack a specific fact or source. Keep necessary
   qualifications and comparisons.
1. Check the argument: each claim should follow from the evidence available in the source material. Do not invent a
   number, citation, causal link, or stronger conclusion to make a sentence sound precise.
1. Check the result for repeated openers, parallel sentence templates, and monotonous rhythm. Preserve useful structure,
   including lists and headings that help readers scan.
1. Compare the revision with the draft. Restore any lost fact, qualification, author preference, or distinctive turn of
   phrase. For this author's register, consult [references/voice.md](references/voice.md).

Surface patterns do not establish AI authorship or writing quality. The linter cannot judge relevance, factual accuracy,
or whether an unusual expression belongs to the author. Do not minimize the finding count at the expense of meaning or
voice.

## Code artifacts

For PRs, commits, comments, docstrings, naming, and code structure, see [references/code.md](references/code.md). Use
`/simp` when Python style work is in scope.

## Quick checks

Before delivering, check for stock openers, hollow contrasts, repeated sentence shapes, unsupported significance, and
unnecessary length. Review adverbs, passive voice, punctuation, and list structure in context; none is a standalone
reason to delete content. Preserve quoted text and code examples.

## Validate

Run `uv run scripts/slop_score.py <file>` from this skill's directory, or pipe a draft on stdin. The script skips
Markdown code spans and fences. `GATE` locates stock phrases to edit before delivery, except deliberate usage the author
requested. `ADVISORY` suggests passages to inspect, including common human usage. `VOICE` reports descriptive rhythm and
punctuation counts; it cannot judge whether the writing sounds like the author. Review each finding against the sentence
and the author's preferences. For source files, `CODE` checks a small set of comment, name, and docstring patterns.
Finish by checking the edited facts and the requested format yourself.

## Examples

See [references/examples.md](references/examples.md).
