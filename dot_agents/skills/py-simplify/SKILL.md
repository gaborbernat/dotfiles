---
name: py-simplify
description: Simplify and tighten Python code and tests to a strict house style (comments and docstrings explain why not what and stay concise, parameterized tests, __all__ exports, Final typing, walrus, late/compact variable definitions). Use when asked to simplify, tidy, or refactor Python for style — not to find bugs.
---

Apply the rules below to the Python files in scope (the current diff, a named file, or the file under discussion). This
is a quality pass: simplify and restyle without changing behavior. It does not hunt for bugs — use `/code-review` for
that.

Read each target file and its siblings first to match existing conventions, then apply every rule that fits. Report what
changed and why. Run the project's tests if test files were touched.

After editing, fix linting before the PR is opened. If the project has a `.lintrc.yaml` at its root, run
`linterator check -l info --fix .` (linterator already runs ruff, so do not also run it separately). Otherwise, run
`ruff format .; ruff check . --fix --unsafe-fixes . --output-format=concise`. Either way, ensure it passes.

These rules cover only what ruff cannot. Anything ruff already enforces and auto-fixes under `select = ["ALL"]` —
argument-count caps (`PLR0913`), `TYPE_CHECKING` import moves (`TC00x`), modern-syntax upgrades (`UP`),
exception-message/`raise ... from` hygiene (`EM`/`B904`), blind-except bans (`BLE001`/`E722`) — is handled by the lint
step above and must not be restated here.

## Rules

1. **Comments and docstrings explain why, not what — concisely.** Delete any comment or docstring that restates what the
   code does. Keep only those giving rationale the code can't show, and keep them as short as possible. Code should be
   self-documenting.

1. **Compact, late variable definitions.** Define each variable as late as possible, immediately before its first use —
   not at the top of a block.

1. **No single-use variables.** A variable used only once must be inlined. Exception: keep the variable when naming it
   makes the code more compact *and* more readable (e.g. it untangles a deeply nested expression).

1. **Walrus where it helps.** Use `:=` whenever it makes the code more compact without hurting readability.

1. **`Final` for constants.** Any variable that is never reassigned — especially at module scope — must be typed
   `Final[<type>]`.

1. **Global naming.** Module-scope variables are `UPPER_CASE`. Those not imported from another business-logic module are
   additionally prefixed with `_` (e.g. `_DEFAULT_TIMEOUT: Final[int] = 30`,
   `_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)`).

1. **Single-letter names only in comprehensions.** Single-character variable names are allowed only as
   comprehension/generator targets (`[x.id for x in rows]`). Everywhere else give a descriptive name.

1. **Explicit exports.** Every name imported and used by other modules must appear in an `__all__ = [...]` list at the
   end of the file. Names only used internally stay out of it.

1. **Fix, never suppress, linter failures.** Resolve every linter finding by fixing the code. Do not add ignore/`noqa`
   directives or disable rules to silence them.

1. **Fix, never suppress, type errors.** Resolve type-checker errors by correcting the types. Never reach for `Any`,
   `object`, or `# type: ignore` to make them go away. When a genuine fix is impossible (e.g. an upstream stub bug), the
   suppression must name the specific error code — never a blanket `# ty: ignore` / `# type: ignore` — and carry an
   inline reason or upstream link, e.g.
   `# ty: ignore[no-matching-overload]  # https://github.com/astral-sh/ty/issues/2428`.

1. **Define after use (reads like a book).** Order every module so each function, method, and class is defined *below*
   the code that uses it: the entry point sits near the top and the helpers it calls follow in first-call order, so the
   file reads top-to-bottom like prose. The only exceptions are genuine runtime ordering requirements — a name that must
   already exist when a line *executes* at import time (a module-scope value, a decorator, a default argument, or a base
   class named in a `class` statement). Type annotations are not a use: `from __future__ import annotations` (Python
   ≤3.13) and PEP 649 lazy evaluation (3.14+) defer them, so never reorder to satisfy an annotation reference.

## Test rules

12. **Parameterize.** Collapse near-duplicate test functions into a single `@pytest.mark.parametrize` using
    `pytest.param(..., id="...")` for each case. Always give a readable `id`.

01. **Fixtures over setup duplication.** Extract repeated setup/teardown into fixtures.

01. **100% diff coverage.** Every line changed in the PR must be covered by tests, measured against the diff versus the
    merge base (not whole-repo coverage). Add tests for any uncovered changed line before the PR is ready.

1. **Test through public APIs only.** Exercise behavior via the module's public interface; never import, call, or assert
    on private (underscore-prefixed) functions, methods, or attributes directly. If private logic needs coverage, drive
    it through the public entry point that uses it.

Keep all other house conventions (type annotations everywhere, one assertion-concept per test, multiple test files over
test classes) intact while applying these.
