---
name: commit
description: Creates git commits following Commitizen conventions. Use when asked to commit changes, create a commit, or prepare staged changes for commit.
---

The commit message should communicate the intent and reasoning behind the changes, not describe what the code does.

## Message Format

Follow Commitizen conventions with a relevant emoji:

```
<emoji> <type>(<scope>): <subject>

<body>
```

**Types**: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

**Emoji by type**:

- ✨ feat - new feature
- 🐛 fix - bug fix
- 📝 docs - documentation
- 💄 style - formatting, no code change
- ♻️ refactor - code restructure
- ⚡ perf - performance improvement
- 🧪 test - adding tests
- 🔧 build/chore - tooling, config
- 👷 ci - CI/CD changes
- ⏪ revert - reverting changes

## Subject Line

- Under 50 characters
- Imperative mood ("add" not "added" or "adds")
- No period at end
- Emoji at start, then type(scope): subject

## Body

Small, self-explanatory changes get a one-line commit. Add a body only when the why isn't obvious from the subject,
written in paragraphs wrapped at 80 characters. Focus on:

1. **Motivation**: What problem does this solve? Why was the change necessary?
1. **Approach**: Why this solution over alternatives? What trade-offs were considered?

Run the message through the `/no-slop` skill before committing.

**Avoid**:

- Describing what the code does line-by-line
- Adding Co-Authored-By with your own name
- Bullet lists of changed files
- Generic messages like "fix bug" or "update code"

**Illustrative example** (follow the format; take the content and length from the change):

```
🐛 fix(auth): prevent session timeout during OAuth flow

Users with high-latency connections were getting logged out mid-authentication
because the session token expired before the OAuth provider responded.

Extended the token validity window specifically for the OAuth callback phase.
This preserves our security model for normal sessions while accommodating
real-world network conditions during the authentication handshake.
```

## Workflow

1. Run `git status` to see what's staged
1. Run `git diff --staged` to review the actual changes
1. Identify the primary purpose (the "why")
1. Write subject line: emoji + type(scope): imperative summary
1. Write body paragraphs explaining motivation and approach, when the change needs one
1. Commit with a heredoc so the message keeps its line breaks:

```bash
git commit -m "$(cat <<'EOF'
<message here>
EOF
)"
```
