# Code Artifacts

This covers the AI-tell layer of code prose. For comments, structure, and other house style run `/simp`; for commit
messages follow `/commit`.

**Naming.** Drop `Manager`/`Handler`/`Helper`/`Util` suffixes on classes that just hold functions. Shorten verbose
compounds (`userDataObject` to `user`). Use one name per concept (no `items`/`entries`/`records` cycling). Use idiomatic
short names.

**Docstrings.** No type-redundant params, no tautological summary (`def save(): "Saves."`). State units, ranges, what it
raises, and edge behavior.
