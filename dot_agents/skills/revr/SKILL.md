---
name: revr
description: Review one pull request, given by number, and draft a GitHub review with comments anchored to diff lines. Use for an adversarial PR review that proposes changes for the user to approve and post, without editing code.
---

Work in the repository selected by the user, or the current repository when none is named. This skill never commits or
pushes code, leaves no edits behind, and never changes PR metadata; its output is a review draft that the user approves
before it is posted.

1. Review the PR whose number the user gave, regardless of author. Without a number, ask for one; never pick PRs
   yourself.
1. Inspect the PR's description, base and head commits, full diff, surrounding code, existing review threads, and
   relevant checks. Use an isolated worktree at the PR's exact head commit so other branches and uncommitted work stay
   intact. Review adversarially for correctness, performance, and maintainability; investigate plausible failures and
   keep only findings supported by evidence (the code path, the dependency's source, a reproducing test run in the
   worktree). Skip a point an existing thread already raises.
1. Search the project's documentation for the behavior, API, command, or setting changed by the PR. Note every page and
   example that the diff makes inaccurate or incomplete, and missing tests for each behavioral change.
1. Read both `/simp` and `/no-slop` in full, including their referenced rules, and audit the **entire PR diff** against
   its merge base, including tests and prose, with `/style`. Each violation is a finding.
1. Turn each finding into one inline comment anchored to the diff line or line range it concerns. A point about the
   whole PR (layout, scope, an approach to rethink) goes in the review body instead. Write as a colleague, using "we"
   for the team ("We drop…", "We reproduced it…").

   A correctness, behavior, build, documentation or maintainability finding uses three bold headings:

    - **Problem**: the observable failure or cost in one or two sentences, stated first. Link the other places in the PR
      with the same issue.
    - **Explanation**: the mechanism. Back each claim with a permalink pinned to a commit SHA and line range: the
      dependency's source, its docs, or the PR's own files at the reviewed head. Say what you ran to confirm it and what
      it printed. Add a mermaid flowchart when the point is how data or control moves between components.
    - **Suggested fix**: the change, starting "We…", with a code block when it is a concrete edit, and the evidence that
      it works: what you ran with the fix applied in the worktree and the result. Name the condition under which an
      alternative is better. Discard the trial edit afterwards; never commit it.

   A style point from `/simp` or `/no-slop` is a one- or two-sentence comment prefixed with `nit:`, phrased as a
   suggestion ("perhaps let's…", "Can we…?") with the reason, and a short code example when prose alone is ambiguous.
1. Write the review body: one to three sentences on where the PR stands and what is left before it can ship, plus any
   whole-PR points. Pick the event: `REQUEST_CHANGES` when any finding is a correctness bug or must be fixed before
   merge, `COMMENT` when everything is optional, `APPROVE` when there are no findings.
1. Validate every anchor against the PR's diff at the reviewed head (`gh api repos/{owner}/{repo}/pulls/{n}/files`): a
   comment's `line`, and `start_line` for a range, must fall inside one hunk of that file, on side `RIGHT` for added or
   context lines and `LEFT` for removed lines. Re-anchor or move to the body any comment that fails.
1. Apply `/no-slop` to every comment and the body, and `/simp` to any code example in them. Repeat after any edit.
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
