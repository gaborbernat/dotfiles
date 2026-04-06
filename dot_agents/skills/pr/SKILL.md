---
name: pr
description: Creates or updates a PR with title, description, assignees, reviewers, and labels. Use when asked to create a PR, update a PR, write or improve a PR title/description, or prepare a pull request for review.
---

First run `git diff upstream/main...HEAD` to understand all changes being proposed. The title and description should communicate the value and reasoning behind the changes, not describe what the code does line-by-line.

## Title Format

Follow Commitizen conventions with 1-2 relevant emoji:

```
<emoji> <type>(<scope>): <short summary>
```

**Types**: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

**Examples**:
- `✨ feat(auth): add OAuth2 support for third-party logins`
- `🐛 fix(api): resolve race condition in request handler`
- `♻️ refactor(core): simplify state management flow`

Keep titles under 72 characters. The emoji goes at the start, pick one that matches the change type.

## Description Format

Write in paragraphs, not bullet lists. Do not start with a header. Use 1-3 emoji sparingly throughout to highlight key points.

**Structure**:

1. **Opening paragraph**: State the motivation. Why was this change needed? What problem does it solve? What's the user or developer benefit?

2. **Approach paragraph**: Explain how the solution works at a high level. Focus on the design decisions and trade-offs, not implementation details.

3. **Impact paragraph** (if applicable): Note any behavioral changes, migration steps, or things reviewers should pay attention to.

**Formatting**:
- Use backticks `` for quoting code, variables, file names, and technical terms (not double quotes "")

**Avoid**:
- Mentioning tests or test coverage
- Describing what specific functions or methods do
- Adding yourself as co-author
- Starting with a header like "## Summary"
- Bullet-point lists of file changes
- AI slop: filler phrases, throat-clearing openers, emphasis crutches, adverbs, vague declaratives, em dashes, passive voice, "not X but Y" contrasts, false agency (inanimate objects doing human verbs)

**Good example**:

```
Users signing in with Google accounts were redirected to an error page because
the session token expired before the OAuth callback completed. 🔐 This became
more frequent as our user base grew internationally, where network latency is
higher.

The fix extends the token validity window during the OAuth flow and adds a
retry mechanism for the callback handler. ✨ This approach preserves our
security model while accommodating real-world network conditions.

Existing sessions remain unaffected. The retry logic uses exponential backoff
to avoid hammering the auth provider.
```

## Labels

Pick applicable labels from `enhancement`, `bug`, `documentation` based on the change type:

- `feat`, `perf`, `refactor`, `style` → `enhancement`
- `fix` → `bug`
- `docs` → `documentation`
- Multiple labels are fine if the PR spans categories

## Workflow

### Creating a new PR

1. Run `git diff upstream/main...HEAD` to see all changes
2. Run `git log upstream/main..HEAD --oneline` to see commit history
3. Identify the primary purpose (what user/developer problem this solves)
4. Draft title following Commitizen format with emoji
5. Write description paragraphs explaining why and how
6. Determine labels from the change type
7. Create with:

```bash
gh pr create --title "..." --body "..." --label "<labels>"
```

### Updating an existing PR

1. Run `git diff upstream/main...HEAD` to see all changes
2. Run `git log upstream/main..HEAD --oneline` to see commit history
3. Identify the primary purpose (what user/developer problem this solves)
4. Draft title following Commitizen format with emoji
5. Write description paragraphs explaining why and how
6. Determine labels from the change type
7. Update with `gh pr edit <number> --title "..." --body "..."` and add missing labels
