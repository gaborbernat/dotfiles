---
name: drift
description: Audit a repository's documentation against its current source and report every place where they disagree. Use when asked to check docs for drift, staleness, or accuracy across a whole project rather than one PR's diff.
---

# drift

Work in the repository selected by the user, or the current repository when none is named. The audit reads and
reports; it changes nothing until the user asks for fixes.

1. Find the documentation: the source tree the docs build reads (`docs/` and the path in `mkdocs.yml`, `conf.py`, or the
   docs tox environment), the README, and other top-level guides. Skip changelogs, release notes, and news fragments:
   they record history and are meant to be outdated. In a Diátaxis project, treat tutorials, how-to guides, reference,
   and explanation as separate passes; a fix that lands in reference often misses the how-to showing the old usage.

2. Find what the code exposes to users: the CLI parser, configuration schema and keys, environment variables, defaults,
   the public API (`__all__`, exported symbols, entry points), plugin hooks, error messages users act on, and supported
   versions in the packaging metadata. This list is the ground truth.

3. Check both directions:

   - **Stale docs**: each command, flag, option, config key, environment variable, default, signature, code example,
     sample output, version requirement, and path a page states. Look it up in the source at `HEAD`.
   - **Undocumented surface**: each user-facing item from step 2 that no page mentions. Internal code is out of scope.

   Confirm each claim by reading the source. Running a documented example confirms it better; ask the user before
   executing anything, then run it in the project's dev environment.

4. For a large doc set, split the pages into groups and give each group to a subagent with the repository path, its
   pages, and step 3. Tell each to keep scratch files under the repository's `target/scratch/`, never in `/tmp`, and to
   return findings with both locations and the evidence. A subagent that fails, times out, or returns nothing did not
   audit: retry it once, then list its pages as not audited. Treat every subagent finding as a claim: check it against
   the source yourself and drop what does not hold.

5. Report only the differences, grouped by page, ranked by how badly a reader following the page would fail. For each:
   the doc location (`path:line`), what it says, what the code does, and the source location that shows it. When the
   page looks right and the code looks wrong, mark it as a possible bug instead of a doc fix. End with the pages not
   audited, if any. If nothing differs, say "No drift detected" and list what was checked.

6. Stop and ask whether to fix. On approval, branch from the default branch and update every affected page, examples
   included, keeping each page in its Diátaxis quadrant. Leave suspected code bugs for the user to decide. Build the
   docs when the project has a docs environment, apply `/no-slop` to every changed paragraph, and open the PR with
   `/commit-pr`.
