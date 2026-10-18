---
name: rev-no-exc
description: Enforce every applicable simp and no-slop rule across a PR's final diff during rev, before its fix commit or push.
---

Use this with `/rev` when its full style pass needs an explicit reminder. It checks the final PR diff against its merge
base; it does not replace the adversarial review.

1. Read `/simp` and `/no-slop` in full, including their referenced rules. Apply every applicable rule to the entire
   final diff: code, tests, comments, and prose. Use only the concrete exceptions those rules allow; do not skip a rule
   because a formatter, linter, or another agent already looked at the file.
1. Run the checks required by those skills and the repository. A passing `/no-slop` gate does not replace its manual
   review. Apply `/no-slop` to the commit message and user-facing report too.
1. After any edit, repeat both passes on the new final diff. Finish this check before committing or pushing.
