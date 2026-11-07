---
name: rev
description: Review and fix one pull request by number, or all open pull requests not authored by the authenticated GitHub user. Use for an adversarial PR review that produces one fix commit per PR and pushes verified fixes.
---

# rev

Work in the repository selected by the user, or the current repository when none is named.

1. If given a PR number, review that PR, regardless of author. Otherwise, get the current account from `gh api user`,
   list every open PR in the repository with pagination, and skip PRs authored by that account. Report when none
   qualify. Review the qualifying PRs one at a time: take each through steps 2 to 9, pushed and reported, before
   starting the next, so a compaction only ever summarizes finished PRs. Run every PR from this session rather than
   handing it to a subagent, which could not start the fresh-context reviewer and validators.

2. Inspect the PR's description, base and head commits, full diff, surrounding code, and relevant checks. Use an
   isolated worktree at the PR's exact head commit so other branches and uncommitted work stay intact. Review
   adversarially for correctness, performance, and maintainability; investigate plausible failures and fix those
   supported by evidence.

3. Search the project's documentation for the behavior, API, command, or setting changed by the PR. Update every page
   and example that the final diff makes inaccurate or incomplete. In a Diátaxis project, check tutorials, how-to
   guides, reference, and explanation separately, then adjust all affected pages and links. Do not add unrelated
   documentation.

4. Follow the repository's instructions and conventions. Add or change tests that demonstrate each behavioral fix, then
   run the relevant checks.

   Read both `/simp` and `/no-slop` in full, including their referenced rules, once per session and again after a
   compaction; when they are already loaded, do not read them again. Apply every rule to the **entire final PR diff**
   against its merge base, including tests and prose. Do not treat a passing `/no-slop` gate as completion: perform its
   full manual review. Apply `/no-slop` to the commit message and user-facing report too. After a further edit, rerun
   both passes on the lines that edit changed, with no skipped rules. Recheck the final diff for regressions and
   unnecessary changes. Run `/style` once the fresh-review rounds of step 5 end, on the final diff and the drafted
   commit message before committing, then on the drafted report before sending it.

5. Have a reviewer with fresh context check the final PR diff, including your uncommitted fixes. Stage your own fixes
   first (`git add -A` in the worktree), so the reviewer's changes stay distinguishable from yours. Spawn an
   `opus-review` subagent and give it only the repository, the worktree path, the merge base, and the PR number.
   Withhold your findings, fixes and reasoning: a reviewer that inherits them inherits their blind spots. Ask it to:

   - review the diff adversarially for correctness, performance, and maintainability, reproducing a suspected bug with a
     test run where it can;
   - skip code the PR does not change, anything a linter or type checker catches, style, and speculation that depends on
     inputs nothing in the code produces;
   - leave tracked files unchanged and keep scratch files under the worktree, never in `/tmp`;
   - return each finding with a severity (blocker, major, nit), its file and line, and the evidence.

   Check `git status` in the worktree after it returns and discard only its unstaged changes and untracked files
   (`git restore .` and `git clean -fd` after reviewing the list), never your staged fixes. A subagent that fails, times
   out, or returns no report did not review: retry it once, then report the review as not run, never as clean.

   Before acting on a blocker or major finding, give it alone to a new `opus-review` validator with the same worktree
   and no other context. It returns confirmed or refuted, quoting the line that decides it. Drop what it cannot confirm.
   Resolve each remaining finding in this session as exactly one of:

   - **Fix**: the finding holds. Apply the fix under the rules of step 4 and rerun the full test suite. A fix that
     removes a guard or broadens an `except` cites, as file:line, the invariant that rules out the guarded case.
   - **Contest**: the finding is wrong, and you quote the line that disproves it. "Intentional" is not evidence, and
     neither is a long rebuttal: only the code is. Having written the fix yourself is no reason to doubt the reviewer.
   - **Escalate**: the finding is wrong only because of knowledge outside the repository, such as a maintainer decision.
     Leave it for the user.
   - **Decline**: a nit not worth changing. Record it.

   Add a comment or a doc line when a human reader needs it, never only because a reviewer without context asked.

   After any fix, run a new round with a new reviewer. Give it only the lines changed since the previous round and their
   callers, plus the contested and declined findings with their evidence so it does not raise them again; still withhold
   your fixes and reasoning. A round is clean when it raises no confirmed blocker or major finding that is not already
   contested, escalated, or declined; a round whose review did not run is not clean. A fixed finding raised again means
   the fix failed: reopen it. Stop at the first clean round. Later rounds produce more invented findings than real ones,
   so after three rounds, or on churn (a new finding at a fix you just applied, which reverting that fix would resolve),
   stop, report the review as not converged with its open findings, and ask the user whether to rethink the approach.

6. Put all fixes in **one new commit on top of the PR's head**. Do not amend, rebase, force-push, or change the PR's
   existing commits. Inspect the staged diff before committing and follow the repository's commit format. If the PR
   needs no changes, do not create an empty commit.

7. Before any push, give the user a concise explanation of what changed and why, the checks run, the number of fresh
   review rounds, each contested or escalated finding with its evidence, and any unresolved issue. Do not post PR
   comments or reviews.

8. Verify the remote PR head is still the commit reviewed. If it moved, recheck the new diff and update the fix and
   checks before pushing. Push only to the PR's head branch, without force. If that branch is not writable, report the
   blocker and leave the local commit available.

9. After a successful push, or if the review found no code fix, use `/pr` to update the PR title, description, and
   labels to match its published diff. If you cannot push, keep the metadata aligned with the published diff. Do not
   post comments or reviews.
