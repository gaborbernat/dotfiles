---
name: fb
description: Address review feedback on one of the user's pull requests. Use when asked to handle, answer, or work through review comments on a PR; it fixes what holds, drafts a reply per thread, and posts nothing without approval.
---

# fb

Work in the repository selected by the user, or the current repository when none is named. This skill changes the PR's
code and drafts replies; it never posts, resolves a thread, or dismisses a review without approval.

1. Use the PR number the user gave, or the open PR for the current branch (`gh pr view --json number`). Ask when neither
   exists.

2. Collect the feedback still open: every unresolved review thread whose last comment is not from the authenticated
   account (`gh api user`), the body of each review that requested changes, and PR comments from others posted after
   your last commit or reply. Fetch threads with GraphQL, paginated, so resolution and outdated state come with them:

   ```bash
   gh api graphql --paginate -f owner=OWNER -f repo=REPO -F n=NUMBER -f query='
     query($owner: String!, $repo: String!, $n: Int!, $endCursor: String) {
       repository(owner: $owner, name: $repo) {
         pullRequest(number: $n) {
           reviewThreads(first: 50, after: $endCursor) {
             pageInfo { hasNextPage endCursor }
             nodes { id isResolved isOutdated path line
               comments(first: 50) { nodes { databaseId author { login } body url } } }
           }
         }
       }
     }'
   ```

   Report when nothing is open, and stop.

3. Work on the PR's head branch, in the current checkout when it is that branch and clean, otherwise in an isolated
   worktree so other branches and uncommitted work stay intact. Read each comment against the code at the current head;
   an outdated thread may already be addressed. Comments from review bots (CodeRabbit, Copilot, Bugbot and the like) are
   claims: confirm each against the code before you call it a fix. When a reviewer's argument is long, read the code and
   form your own view before reading their reasoning; a detailed rebuttal sways a model more than its evidence warrants.

4. Classify each piece of feedback as exactly one of:

   - **Fix**: the point holds, in full or in part. Fix the part that holds and say which part does not.
   - **Contest**: the point is wrong, and you cite evidence the reviewer can check in one click: a permalink pinned to a
     commit SHA, a test you ran and its output, the dependency's source or docs. "Intentional" is not evidence. You
     wrote the code; wanting to defend it is not evidence either.
   - **Escalate**: the answer depends on knowledge outside the repository (a maintainer's decision, a release plan, a
     trade-off only the user can make), or the reviewer states such knowledge. Ask the user.
   - **Decline**: a nit or an out-of-scope request not worth doing in this PR. Give the reason; offer a follow-up issue
     when the request has merit.

   A question is a comprehension gap, not an attack: if the reviewer could not follow the code, a later reader will not
   either. Answer it, and fix the code or its comment when a reader needs the answer there, not only the reviewer.

5. Ask about every escalated item at once before editing, then reclassify each with the user's answer.

6. Apply the fixes following the repository's instructions and conventions. Add or change tests that show each
   behavioral fix, and run the relevant checks. Read `/simp` and `/no-slop` in full and apply them to the changed lines;
   audit the final diff and commit messages with `/style`. Commit on top of the head, split by concern; never amend,
   rebase, or force-push, so reviewers can see what changed since their review. Push to the head branch.

7. Draft one reply per thread or review, in the reviewer's thread, as a colleague using "we". Lead with the outcome: for
   a fix, what changed and the commit as a full URL; for a contest, the evidence with its permalink; for a decline, the
   reason. Link every issue, PR, commit, file or line as a full URL, never a bare `#123` or SHA. Apply `/no-slop` to
   each draft.

8. Present to the user: the commits pushed, then each draft as the thread URL, its class, and the reply text. Stop. Post
   nothing until the user approves; approval covers only the drafts shown. After approval, post each reply in its thread
   and report the URLs:

   ```bash
   gh api repos/{owner}/{repo}/pulls/{n}/comments/{comment_id}/replies -f body=@reply.md
   ```

   Answer a review body or PR comment with `gh pr comment {n} --body-file reply.md`. Leave threads unresolved for the
   reviewer.

9. If the fixes changed what the PR does, use `/pr` to update its title, description, and labels.
