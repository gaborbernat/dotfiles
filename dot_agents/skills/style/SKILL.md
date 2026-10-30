---
name: style
description: Audit every applicable simp and no-slop rule on a PR's final diff, commit message, and report during rev or a requested full style pass.
---

# style

Use this for a full PR style pass. The `/no-slop` scorer checks only some patterns; its result is never evidence that
the manual pass is complete.

1. Read `/simp` and `/no-slop` in full. Read every `/no-slop` reference they point to: phrases, lexicon, structures,
   voice, code, and examples. Inspect the entire final PR diff against its merge base, including code, tests, comments,
   docstrings, documentation, and other prose. Check documentation and docstrings against the source files' line limit.
2. Make a rule-by-rule audit in working notes. Give each `/simp` Common rule, each applicable Python rule, and each
   `/no-slop` instruction and listed pattern an outcome: applied, inapplicable with a reason, or an exception with the
   concrete necessity allowed by that rule. Check every relevant changed line against every entry. A tool pass or
   another agent's claim cannot fill in the audit. Fix findings and revisit the affected entries after each edit.
3. Run the repository checks required by `/simp` and `/no-slop`, including the scorer. Judge its findings manually; then
   finish the entries it cannot check. Audit the drafted commit message before committing and the actual user-facing
   report before sending it. If either draft changes, audit it again. Do not claim a full pass while entries remain
   unchecked. Report any exceptions with their reasons.
