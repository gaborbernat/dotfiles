---
name: commit
description: Creates git commits following Commitizen conventions. Use when asked to commit changes, create a commit, or prepare staged changes for commit.
---

The commit message should state the intended outcome and preserve reasoning that cannot readily be inferred from the
diff.

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

Small, self-explanatory changes get a one-line commit. Add a body only when the subject and diff do not explain why the
implementation was chosen. Use concise paragraphs wrapped at 80 characters.

Record relevant constraints and trade-offs, with links to upstream dependency documentation, issues, specifications, or
prior art that support the decision. Research those references when needed; do not invent a rationale to fill a body.
For complex changes, concise architectural prose can explain how the main components interact and why they are arranged
that way. Put diagrams in the PR description when they add meaningful context beyond the prose.

Run the message through `/no-slop` before committing. Review generated prose yourself rather than leaving the reader to
extract the useful context. Apply the same writing standard regardless of who or what drafted it.

**Avoid**:

- Describing what the code does line-by-line
- Routine validation reports, test counts, coverage totals, and CI status
- Lists of unchanged behavior, absent changes, or completed checklist items
- Conversation history and line-by-line implementation walkthroughs
- Adding Co-Authored-By with your own name
- Bullet lists of changed files
- Generic messages like "fix bug" or "update code"

**Illustrative example** (follow the format; take the content and length from the change):

```
🐛 fix(auth): allow time for OAuth consent

The login token can expire while the user is still at the provider. The
normal session timeout is too short for a long consent step.
```

## Workflow

1. Run `git status` to see what's staged
1. Run `git diff --staged` to review the actual changes
1. Identify the primary purpose (the "why")
1. Write subject line: emoji + type(scope): imperative summary
1. Add rationale and supporting references only when the subject and diff leave a decision unexplained
1. Commit with a heredoc so the message keeps its line breaks:

```bash
git commit -m "$(cat <<'EOF'
<message here>
EOF
)"
```
