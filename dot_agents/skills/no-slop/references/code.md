# Code artifacts

This covers the AI-tell layer of code prose. For comments, structure, and other house style run `/simp`; for commit
messages follow `/commit`.

**Naming.** Drop `Manager`/`Handler`/`Helper`/`Util` suffixes on classes that just hold functions. Shorten verbose
compounds (`userDataObject` to `user`). Use one name per concept (no `items`/`entries`/`records` cycling). Use idiomatic
short names.

**Docstrings.** No type-redundant params, no tautological summary (`def save(): "Saves."`). State units, ranges, what it
raises, and edge behavior.

**Commits and PRs.** Check each claimed change against the diff and cut any the diff does not contain. Claims of changes
that were never implemented are the largest class of message-code mismatch, and PRs with a high mismatch were accepted
at 28.3%, against 80.0% in the comparison group ([arXiv 2601.04886](https://arxiv.org/abs/2601.04886)). Cut assurances
that state no fact: "while preserving", "while maintaining", "ensures", "without breaking". Cut "verified" unless the
sentence names the test that ran.
