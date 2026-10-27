---
name: revr
description: Review one pull request by number, or all open pull requests not authored by the authenticated GitHub user, and draft a GitHub review with comments anchored to diff lines. Use for an adversarial PR review that proposes changes for the user to approve and post, without editing code.
---

Work in the repository selected by the user, or the current repository when none is named. This skill never edits,
commits or pushes code and never changes PR metadata; its output is a review draft that the user approves before it is
posted.

1. If given a PR number, review that PR, regardless of author. Otherwise, get the current account from `gh api user`,
   list every open PR in the repository with pagination, and skip PRs authored by that account. Report when none
   qualify.
1. Inspect each PR's description, base and head commits, full diff, surrounding code, existing review threads, and
   relevant checks. Use an isolated worktree at the PR's exact head commit so other branches and uncommitted work stay
   intact. Review adversarially for correctness, performance, and maintainability; investigate plausible failures and
   keep only findings supported by evidence (the code path, the dependency's source, a reproducing test run in the
   worktree). Skip a point an existing thread already raises.
1. Search the project's documentation for the behavior, API, command, or setting changed by the PR. Note every page and
   example that the diff makes inaccurate or incomplete, and missing tests for each behavioral change.
1. Read both `/simp` and `/no-slop` in full, including their referenced rules, and audit the **entire PR diff** against
   its merge base, including tests and prose, with `/style`. Each violation is a finding.
1. Turn each finding into one inline comment anchored to the diff line or line range it concerns, written the way the
   user reviews a teammate's PR:

    - Write to the author as a colleague, using "we" for team practice. Phrase a request as a question or suggestion
      ("Can we…?", "perhaps let's…", "I would prefer…") and give the reason: the failure it causes, the maintenance
      cost, or the convention it breaks.
    - Prefix a minor style point with `nit:`.
    - Link the evidence: the library source, a related PR or issue, another repository that does it the way you suggest.
    - Show the change with a short code example when prose alone would be ambiguous.
    - One finding per comment, anchored where the change belongs. A point about the whole PR (layout, scope, an approach
      to rethink) goes in the review body instead.
1. Write the review body: a short overall take that opens with what the PR gets right when it does, then the themes that
   matter most. Pick the event: `REQUEST_CHANGES` when any finding is a correctness bug or must be fixed before merge,
   `COMMENT` when everything is optional, `APPROVE` when there are no findings.
1. Validate every anchor against the PR's diff at the reviewed head (`gh api repos/{owner}/{repo}/pulls/{n}/files`): a
   comment's `line`, and `start_line` for a range, must fall inside one hunk of that file, on side `RIGHT` for added or
   context lines and `LEFT` for removed lines. Re-anchor or move to the body any comment that fails.
1. Apply `/no-slop` to every comment and the body, then use `/style` to audit the draft. Repeat after any edit.
1. Present the draft to the user and stop: the event, the body, then each comment as `path:line` (or `path:start-end`)
   with its text, ranked by severity. Do not post anything until the user approves; apply their edits and present again
   when they change the draft. Approval covers only the draft shown.
1. After approval, verify the remote PR head is still the reviewed commit. If it moved, recheck the new diff, re-anchor
   the comments, and present the changes before posting. Post the review in one call, pinned to the reviewed commit:

   ```bash
   gh api repos/{owner}/{repo}/pulls/{n}/reviews --input - <<'EOF'
   {
     "commit_id": "<reviewed head sha>",
     "event": "REQUEST_CHANGES",
     "body": "<review body>",
     "comments": [
       {"path": "src/app.py", "line": 42, "side": "RIGHT", "body": "<comment>"},
       {"path": "src/app.py", "start_line": 50, "line": 55, "side": "RIGHT", "start_side": "RIGHT", "body": "<comment>"}
     ]
   }
   EOF
   ```

   Report the review URL from the response.
