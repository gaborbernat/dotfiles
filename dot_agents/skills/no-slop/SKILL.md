---
name: no-slop
description: Remove AI writing patterns from prose and code artifacts (PRs, commits, comments, docstrings, docs). Use when drafting, editing, or reviewing text to eliminate predictable AI tells like filler, throat-clearing, emphasis crutches, vague declaratives, and formulaic structures.
---

Strip AI tells, then restore a human voice. Two passes.

## Pass 1 — strip

1. Cut filler: throat-clearing openers, emphasis crutches, all adverbs. See
   [references/phrases.md](references/phrases.md).
1. Cut AI vocabulary and copula avoidance. See [references/lexicon.md](references/lexicon.md).
1. Break formulaic structures: binary contrasts, negative listing, dramatic fragmentation, rhetorical setups, false
   agency, significance inflation, elegant variation, copula chains. See
   [references/structures.md](references/structures.md).
1. Active voice, human subject. No passive, no inanimate actors.
1. Be specific. No vague declaratives, no lazy extremes (every/always/never).
1. Vary rhythm. Mix sentence lengths, two items beat three. No em dashes, no colon-drama, no markdown over-structuring.
1. Trust readers. State facts directly; no softening, no quotables.

## Pass 2 — voice

Restore a human voice without re-adding slop. See [references/voice.md](references/voice.md).

## Code artifacts

PRs, commits, comments, docstrings, naming, structure: see [references/code.md](references/code.md). For Python style
run `/simp`.

## Quick checks

Before delivering:

- Adverb, passive voice, inanimate actor, Wh-opener, "here's what/this" → cut or recast.
- "not X, it's Y" contrast, three same-length sentences, punchy one-line ending → state directly, vary.
- Em dash, drama colon, over-structured markdown, a phrase repeated across paragraphs → remove.
- AI-word (lexicon), vague declarative, significance inflation → name the specific thing.

## Validate

The rules above are the work. Apply every one of them by hand to every draft — phrases, structures, lexicon, voice, and
code. That is what de-slopping is.

The script is a dumb backstop that matches a small hardcoded subset of patterns. A 100/100 is necessary but never
sufficient: text can score 100 and still be slop. Never treat the gate as the goal, as "done," or as a substitute for
the rules.

After applying every rule, run the gate as a final floor: `uv run scripts/slop_score.py <file>` (resolve the path
against this skill's directory; pipe text on stdin when there's no file). A score below 100 means you missed obvious
hits — fix them and rerun. A 100 means keep going on everything the script can't see. Then confirm every fact survived.

## Examples

See [references/examples.md](references/examples.md).
