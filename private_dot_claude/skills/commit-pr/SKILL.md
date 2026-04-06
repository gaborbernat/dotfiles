---
name: commit-pr
description: Creates a git commit and then opens a pull request. Use when asked to commit and create a PR in one step.
---

Complete the following steps in order:

1. First, invoke the `/commit` skill to create a commit
2. Then, invoke the `/pr` skill to create or update a pull request

Pass through any arguments from the user (e.g. "team PR") to the `/pr` skill.
