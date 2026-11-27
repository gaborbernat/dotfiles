---
name: rev
description: Review and fix one pull request by number, or all open pull requests not authored by the authenticated GitHub user. Use for an adversarial PR review that produces one fix commit per PR, pushes verified fixes, and drives the PR's CI to green.
---

# rev

Work in the repository selected by the user, or the current repository when none is named.

1. If given a PR number, review that PR, regardless of author. Otherwise, get the current account from `gh api user`,
   list every open PR in the repository with pagination, and skip PRs authored by that account. Report when none
   qualify. Review the qualifying PRs one at a time: take each through steps 2 to 9, pushed, green and reported, before
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

   Keep every piece of prose you write concise and to the point: PR bodies, commit messages, changelog entries, code
   comments, and the supersede closing comment. Lead with the change and its effect, say each fact once, and cut filler,
   hedging, and restated context. Where one makes the point faster than a sentence, show a real example taken from this
   work, such as the failing config, the command run, or its actual output, never an invented one. Add a mermaid diagram
   only when it explains faster than prose, such as a flow across components; most PRs need none.

   Use plain words a newcomer follows and explain technical jargon instead of assuming it: spell out shorthand such as
   `deps` or `TTL` (`dependencies`, `time to live`), and expand an acronym the reader may not know on first use. Link
   what you mention where you mention it, on the words that name it (the issue, the code line, the upstream
   documentation), never in a separate list of links.

   Keep the PR minimal: it changes only what its purpose and your fixes need. Treat a change outside that scope, in the
   PR or in your own fixes, as a finding and revert it in the fix commit. When the reverted change is valid on its own,
   open it as a separate PR with `/pr` from a new branch on your fork, crediting its original author, and link that PR
   in the report.

   Code the PR only moves counts as unchanged, so the `/simp` pass leaves it as it was. Refactor only when the change is
   medium to large and would otherwise add real maintenance or readability cost, such as a function that grows past one
   task or logic duplicated across callers; then do the refactor and keep the public API backwards compatible, with the
   same names, signatures, and behavior for existing callers.

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
   checks before pushing. Push only to the PR's head branch, without force. When the author has not enabled "Allow edits
   by maintainers" (`maintainerCanModify` is false), supersede the PR instead: push its commits unchanged plus your fix
   commit to a new branch on your own fork, open a PR from it with `/pr` whose description says `Supersedes #<number>`
   and credits the original author. Then close the original with `gh pr close --comment`, saying it was closed because
   maintainer edits are disabled and linking the new PR; this closing comment is the one comment the skill posts without
   asking. If the push fails for another reason, report the blocker and leave the local commit available.

9. After a successful push, or if the review found no code fix, use `/pr` to update the PR title, description, and
   labels to match its published diff; a superseding PR gets them when `/pr` opens it. If you cannot push, keep the
   metadata aligned with the published diff. Do not post comments or reviews.

   Then drive the PR's checks to green; a PR is not done while a required check fails or waits. Workflow runs from a
   fork can wait for maintainer approval (`gh run list --commit <head sha>` shows them as `action_required`). Approve
   them only once the head is a commit you reviewed and, when the review produced fixes, only after your fix commit is
   pushed, so the approved run tests your changes and never code you have not read: approve each waiting run at that
   head with `gh api -X POST repos/<owner>/<repo>/actions/runs/<run id>/approve`. A newer head pushed by someone else
   goes back to step 8 first.

   Watch with `gh pr checks <number> --watch`. For each failure, read its log (`gh run view <run id> --log-failed`),
   reproduce it locally or on `winvm`, and fix the cause under the rules of step 4 in a further commit on top, never
   amending or force-pushing; push it as in step 8, then watch again. Never skip, disable or mark a check optional to
   make it pass, and rerun a job only when its log shows an infrastructure failure, saying so. A failure the PR did not
   cause, such as one that also fails on the base branch, is reported with the evidence instead of fixed here. Report
   the final state of every check.
