# Code Artifacts

For Python house style run `/simp`; this covers the AI-tell layer.

**Comments.** Delete tautological comments (`i += 1  # increment i`), section banners (`# --- helpers ---`), narrator
"we" comments, prose padding above a one-liner, and comments that repeat the docstring. Keep only a non-obvious why.

**Naming.** Drop `Manager`/`Handler`/`Helper`/`Util` suffixes on classes that just hold functions. Shorten verbose
compounds (`userDataObject` to `user`). Use one name per concept (no `items`/`entries`/`records` cycling). Use idiomatic
short names.

**Commits.** Imperative present, naming the concrete change. No vague verbs ("improve", "update", "enhance"), no passive
or past tense, no "various"/"several" bundling, no body that restates the diff.

**Docstrings.** No type-redundant params, no tautological summary (`def save(): "Saves."`). State units, ranges, what it
raises, and edge behavior.

**Structure.** Inline single-use wrappers. Delete speculative `else`/`elif` for states that can't occur. Remove dead
exports. Drop `try/except` around non-throwing one-liners. Strip leftover `print`/`console.log`/debug logs. Extract
blocks repeated across files.
