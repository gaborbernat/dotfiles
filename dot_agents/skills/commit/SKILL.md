---
name: commit
description: Creates git commits following Commitizen conventions. Use when asked to commit changes, create a commit, or prepare staged changes for commit.
---

# Commit

When creating a commit, first run `git diff --staged` to understand what's being committed. The commit message should
communicate the intent and reasoning behind the changes, not describe what the code does.

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

A small, self-explanatory change gets a one-line commit. Add a body only when the subject and diff leave the why
unexplained, written in paragraphs wrapped at 80 characters. Focus on:

1. **Motivation**: What problem does this solve? Why was the change necessary?
2. **Approach**: Why this solution over alternatives? What trade-offs were considered?

**Avoid**:

- Describing what the code does line-by-line
- Adding Co-Authored-By with your own name
- Bullet lists of changed files
- Generic messages like "fix bug" or "update code"
- Routine validation reports, test counts, coverage totals, and CI status
- Lists of unchanged behavior, absent changes, or completed checklist items
- Conversation history
- AI slop: filler phrases, throat-clearing openers, emphasis crutches, adverbs, vague declaratives, em dashes, passive
  voice, "not X but Y" contrasts

**Good example**:

```
🐛 fix(auth): keep sessions alive during OAuth

Users with high-latency connections were getting logged out mid-authentication
because the session token expired before the OAuth provider responded.

Extended the token validity window specifically for the OAuth callback phase.
This preserves our security model for normal sessions while accommodating
real-world network conditions during the authentication handshake.
```

## Workflow

1. Run `git status` to see what's staged
2. Run `git diff --staged` to review the actual changes
3. Identify the primary purpose (the "why")
4. Write subject line: emoji + type(scope): imperative summary
5. Write body paragraphs explaining motivation and approach
6. Write the message to a file, then commit with `git commit -F <file>`. Never pass it inline: `-m` hands backticks and
   `$(...)` to the shell as command substitution, and the heredoc workaround does not exist in every shell (fish has no
   heredocs at all)
