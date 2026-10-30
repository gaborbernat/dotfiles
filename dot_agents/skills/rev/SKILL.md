---
name: rev
description: Review and fix one pull request by number, or all open pull requests not authored by the authenticated GitHub user. Use for an adversarial PR review that produces one fix commit per PR and pushes verified fixes.
---

# rev

Work in the repository selected by the user, or the current repository when none is named.

1. If given a PR number, review that PR, regardless of author. Otherwise, get the current account from `gh api user`,
   list every open PR in the repository with pagination, and skip PRs authored by that account. Report when none
   qualify.

2. Inspect each PR's description, base and head commits, full diff, surrounding code, and relevant checks. Use an
   isolated worktree at the PR's exact head commit so other branches and uncommitted work stay intact. Review
   adversarially for correctness, performance, and maintainability; investigate plausible failures and fix those
   supported by evidence.

3. Search the project's documentation for the behavior, API, command, or setting changed by the PR. Update every page
   and example that the final diff makes inaccurate or incomplete. In a Diátaxis project, check tutorials, how-to
   guides, reference, and explanation separately, then adjust all affected pages and links. Do not add unrelated
   documentation.

4. Follow the repository's instructions and conventions. Add or change tests that demonstrate each behavioral fix, then
   run the relevant checks.

   Read both `/simp` and `/no-slop` in full, including their referenced rules, and apply every rule to the **entire
   final PR diff** against its merge base, including tests and prose. Do not treat a passing `/no-slop` gate as
   completion: perform its full manual review. Apply `/no-slop` to the commit message and user-facing report too. Repeat
   both passes after any further edit, with no skipped rules. Recheck the final diff for regressions and unnecessary
   changes. Use `/style` to audit the diff and commit message before committing, then the drafted report before sending
   it.

5. Put all fixes for each PR in **one new commit on top of its head**. Do not amend, rebase, force-push, or change the
   PR's existing commits. Inspect the staged diff before committing and follow the repository's commit format. If the PR
   needs no changes, do not create an empty commit.

6. Before any push, give the user a concise explanation for each PR of what changed and why, the checks run, and any
   unresolved issue. Do not post PR comments or reviews.

7. Verify each remote PR head is still the commit reviewed. If it moved, recheck the new diff and update the fix and
   checks before pushing. Push only to the PR's head branch, without force. If that branch is not writable, report the
   blocker and leave the local commit available.

8. After a successful push, or if the review found no code fix, use `/pr` to update the PR title, description, and
   labels to match its published diff. If you cannot push, keep the metadata aligned with the published diff. Do not
   post comments or reviews.
