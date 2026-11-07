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

5. Have a reviewer with fresh context check the final PR diff, including your uncommitted fixes. Spawn a subagent and
   give it only the repository, the worktree path, the merge base, and the PR number. Withhold your findings, fixes and
   reasoning: a reviewer that inherits them inherits their blind spots. Ask it to review the diff adversarially for
   correctness, performance, and maintainability without editing tracked files, to keep any scratch files under the
   worktree and never in `/tmp`, and to return each finding with a severity (blocker, major, nit), its file and line,
   and the evidence. A subagent that fails, times out, or returns no report did not review: retry it once, then report
   the review as not run, never as clean.

   Resolve each finding in this session as exactly one of:

   - **Fix**: the finding holds. Apply the fix under the rules of step 4.
   - **Contest**: the finding is wrong, and you cite evidence the reviewer could read, such as a file and symbol, a test
     run, or the PR description. "Intentional" is not evidence. Having written the fix yourself is no reason to doubt
     the reviewer.
   - **Escalate**: the finding is wrong only because of knowledge outside the repository, such as a maintainer decision.
     Leave it for the user.
   - **Decline**: a nit not worth changing. Record it.

   Add a comment or a doc line when a human reader needs it, never only because a reviewer without context asked.

   After any fix, run a new round with a new subagent. A round is clean when it raises no blocker or major finding that
   is not already contested, escalated, or declined; a round whose review did not run is not clean. A fixed finding
   raised again means the fix failed: reopen it. Stop after two consecutive clean rounds. Stop and ask the user after
   five rounds, or on churn: a new finding at a fix you just applied, which reverting that fix would resolve.

6. Put all fixes for each PR in **one new commit on top of its head**. Do not amend, rebase, force-push, or change the
   PR's existing commits. Inspect the staged diff before committing and follow the repository's commit format. If the PR
   needs no changes, do not create an empty commit.

7. Before any push, give the user a concise explanation for each PR of what changed and why, the checks run, the number
   of fresh review rounds, each contested or escalated finding with its evidence, and any unresolved issue. Do not post
   PR comments or reviews.

8. Verify each remote PR head is still the commit reviewed. If it moved, recheck the new diff and update the fix and
   checks before pushing. Push only to the PR's head branch, without force. If that branch is not writable, report the
   blocker and leave the local commit available.

9. After a successful push, or if the review found no code fix, use `/pr` to update the PR title, description, and
   labels to match its published diff. If you cannot push, keep the metadata aligned with the published diff. Do not
   post comments or reviews.
