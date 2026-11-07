---
name: drift
description: Audit a repository's documentation against its current source and report every place where they disagree. Use when asked to check docs for drift, staleness, or accuracy across a whole project rather than one PR's diff.
---

# drift

Work in the repository selected by the user, or the current repository when none is named. The audit reads and reports;
it changes nothing until the user asks for fixes.

1. Find the documentation: the source tree the docs build reads (`docs/` and the path in `mkdocs.yml`, `conf.py`, or the
   docs tox environment), the README, and other top-level guides. Skip changelogs, release notes, and news fragments:
   they describe past releases. In a Diátaxis project, treat tutorials, how-to guides, reference, and explanation as
   separate passes; a fix that lands in reference often misses the how-to showing the old usage.

2. Find what the code exposes to users: the CLI parser, configuration schema and keys, environment variables, defaults,
   the public API (`__all__`, exported symbols, entry points), plugin hooks, error messages users act on, and supported
   versions in the packaging metadata. This list is the ground truth.

3. Check both directions:

   - **Stale docs**: each command, flag, option, config key, environment variable, default, signature, code example,
     sample output, version requirement, and path a page states. Look it up in the source at `HEAD`.
   - **Undocumented surface**: each user-facing item from step 2 that no page mentions. Internal code is out of scope.

   Start with the deterministic checks the project supports, run in its dev environment: `cog --check` where cog is
   used, the docs build with its link check, Sybil, pytest-examples or doctest when configured, and a grep of every code
   identifier the docs name against `HEAD`. Then confirm the remaining claims by reading the source. Running a
   documented example those checks do not cover confirms it better; ask the user before executing it.

4. For a large doc set, split the pages into groups and give each group to a subagent with the repository path, its
   pages, and step 3. Tell each to keep scratch files under the repository's `target/scratch/`, never in `/tmp`, and to
   return findings with both locations and the evidence. A subagent that fails, times out, or returns nothing did not
   audit: retry it once, then list its pages as not audited. Treat every subagent finding as a claim: check it against
   the source yourself and drop what does not hold.

5. Report only the differences, grouped by page, ranked by how badly a reader following the page would fail. For each:
   the doc location (`path:line`), what it says, what the code does, the source location that shows it, and how it was
   confirmed. At equal impact, list findings confirmed by a check or a missing identifier before those inferred from
   reading, which are wrong far more often. When the page looks right and the code looks wrong, mark it as a possible
   bug instead of a doc fix. End with the pages not audited, if any. If nothing differs, say "No drift detected" and
   list what was checked.

6. Stop and ask whether to fix. On approval, branch from the default branch and update every affected page, examples
   included, keeping each page in its Diátaxis quadrant. Leave suspected code bugs for the user to decide. Build the
   docs when the project has a docs environment, apply `/no-slop` to every changed paragraph, and open the PR with
   `/commit-pr`.
