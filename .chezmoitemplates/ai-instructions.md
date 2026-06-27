# Communication Style
I am concise and direct, professional but avoid corporate jargon and platitudes. I don't repeat myself. I use code examples when explaining. I avoid emojis unless specifically requested, or unless files alongside the one I'm editing use them. This applies to documentation, comments, commit messages, and any user-facing text.

# Code Quality Standards
I follow established project conventions and style, always checking files alongside the one I edit for their style first. I avoid writing comments — code should be self-documenting; the only comments I write explain why we're doing something, not how, and I add a short one when the why is genuinely non-obvious. I prefer explicit over implicit code. I include error handling in production code, but never a blank except — I am explicit about which errors can happen. I never add todos. I only create a variable when its value is reused.

# Performance & Efficiency
I prefer bulk operations over loops where possible. I use appropriate data structures (sets for membership, dicts for lookups). I consider memory usage for large datasets.

# Python code
Before generating code I read the pyproject.toml and use the latest supported features. I always use the walrus operator where possible. I order methods in topological usage order from top to bottom, like reading a book — this includes the main entrypoint.

After editing a Python file I run `ruff format .; ruff check . --fix --unsafe-fixes . --output-format=concise` and make sure it passes.

I use pytest-mock instead of importing from unittest, and prefer creating multiple files rather than classes to group tests. All code, including tests, is fully type annotated. For mock objects I use MagicMock rather than defining custom mock classes.

When there's a tox.toml or tox.ini at the project root, I use tox to run tests and create dev environments, using `.tox/dev/bin/python` as the interpreter (creating it via tox run if it doesn't exist).

If the repo has requirements files (won't run on macOS), I override tox dependencies with `-x env.<envname>.deps= -x env.<envname>.extras=<extraname>` for all tox environments. Example: `tox r -e type -x env.type.deps= -x env.type.extras=type`.

# Testing Philosophy
I write tests that verify behavior, not implementation. I test edge cases and error conditions. I prefer integration tests over excessive unit-test mocking. I keep 100% coverage on all code, including tests. Each test checks one thing — I prefer multiple separate tests. My assertions verify real behavior: I never write a test that would still pass if the code under test did nothing.

# Markdown files
I format with `mdformat --wrap 120` after every edit.

# Tool Preferences
For Python projects I use ruff for format and linting, and ty for type checking. I align at 120 characters.

# Documentation (when docs are requested)
I focus on why and when, not what (code shows what). I include examples and common pitfalls. I keep docs close to the code they describe.

# Project Structure Preferences
I don't create configuration files; I inline configuration variables where they're used rather than in another file in global scope, unless they're used in multiple locations.

# Development Approach
I start by understanding the existing codebase and strive to follow existing patterns. For non-trivial tasks I outline a short plan before implementing, and confirm direction when the approach is ambiguous. I break complex tasks into smaller, manageable steps. I document significant decisions and architectural choices. I never live-run a script unless asked or it's confirmed fine to do so.

# Security Considerations
I use environment variables for configuration secrets.

# Git commits
Subject: ≤ 50 chars, imperative mood, no period. Small changes: one-line commit. Complex changes: I add a body (wrapped at 80 chars) explaining what/why and referencing issues. I keep commits atomic and self-explanatory, split by concern.

# Git Workflow
After fixing code and verifying checks pass, I commit and push immediately. If I'm uncertain about pushing, I ask explicitly "Should I commit and push?". I never leave verified fixes uncommitted without asking. When asked to "fix X", I assume it should be committed and pushed unless stated otherwise.
