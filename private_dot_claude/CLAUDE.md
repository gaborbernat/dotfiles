# Communication Style
Be concise and direct, professional but avoid corporate jargon and platitudes. Don't repeat yourself. Use code examples when explaining. Avoid emojis unless specifically requested, or files alongside it has it. This applies in documentation, comments, commit messages, and any user-facing text.

# Code Quality Standards
Follow established project conventions and style by always checking first files alongside the one to edit for their style. Avoid writing comments, code should be self-documenting; the only comments that should exist explain why we're doing something, not how. Prefer explicit over implicit code. Include error handling in production code, but don't use blank exception - be explicit on what errors can happen. Never add todos. Only create variables if that value is re-used.

# Performance & Efficiency
Prefer bulk operations over loops when possible. Use appropriate data structures (sets for membership, dicts for lookups). Consider memory usage for large datasets.

# Python code
Before generating code read the pyproject.toml and use latest supported features. Always use the walrus operator where possible. Methods should be ordered in topological usage order from top to bottom like you'd read a book, this includes the main entrypoint.

Run `ruff format .; ruff check . --fix --unsafe-fixes . --output-format=concise` after editing Python file and make sure it passes.

Use pytest-mock instead of importing from unittest, prefer creating multiple files rather than classes to group tests. All code, including tests must be fully type annotated. For mock objects use MagicMock rather than defining custom mock classes.

When there's a tox.toml or tox.ini file at project root: use tox to run tests and create dev environments. Use the .tox/dev/bin/python as the interpreter (create it via tox if does not exist via tox run).

If the repo has requirements files (won't run on macOS): override tox dependencies with `-x env.<envname>.deps= -x env.<envname>.extras=<extraname>` for all tox environments. Example: `tox r -e type -x env.type.deps= -x env.type.extras=type`.

# Testing Philosophy
Write tests that verify behavior, not implementation. Test edge cases and error conditions. Prefer integration tests over excessive unit test mocking. We need 100% coverage on all code, including tests. One test should test one thing, prefer multiple separate tests.

# Markdown files
Should be formatted with `mdformat --wrap 120` after every edit.

# Tool Preferences
For Python projects we use ruff for format and linting, and ty for type checking. Align at 120 characters.

# Documentation (when docs are requested)
Focus on why and when, not what (code shows what). Include examples and common pitfalls. Keep docs close to code they describe.

# Project Structure Preferences
Don't create configuration files, configuration variables should be inlined where it's used rather than in another file in global scope, unless used in multiple locations.

# Development Approach
Start with understanding the existing codebase, and strive to follow existing patterns. Break down complex tasks into smaller, manageable steps. Document significant decisions and architectural choices. Never live run a script unless asked/confirmed it's fine to.

# Security Considerations
Use environment variables for configuration secrets.

# Git commits
Subject: ≤ 50 chars, imperative mood, no period. Small changes: one-line commit. Complex changes: add body (wrap at 80 chars) explaining what/why; reference issues. Keep commits atomic and self-explanatory; split by concern.

# Git Workflow
After fixing code and verifying checks pass, immediately commit and push. If uncertain about pushing, ask explicitly "Should I commit and push?". Never leave verified fixes uncommitted without asking. When user asks to "fix X", assume they want it committed and pushed unless stated otherwise.
