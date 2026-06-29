---
name: simp
description: Simplify and tighten code and tests to a strict house style — concise why-not-what comments, parameterized tests, explicit exports, late/compact definitions, idiomatic typing. Python rules are defined; other languages follow the same spirit. Use when asked to simplify, tidy, or refactor for style — not to find bugs.
---

Apply the rules below to the files in scope (the current diff, a named file, or the file under discussion). This is a
quality pass: simplify and restyle without changing behavior. It does not hunt for bugs — use `/code-review` for that.

Read each target file and its siblings first to match existing conventions, then apply every rule that fits. Report what
changed and why. Run the project's tests if test files were touched.

Rules are organized per language. Only **Python** is defined today. When working in another language, apply the *spirit*
of the matching Python rule — its closest idiomatic equivalent — until a dedicated section for that language exists.

## Python

After editing, fix linting before the PR is opened. If the project has a `.lintrc.yaml` at its root, run
`linterator check -l info --fix .` (linterator already runs ruff, so do not also run it separately). Otherwise, run
`ruff format .; ruff check . --fix --unsafe-fixes . --output-format=concise`. Either way, ensure it passes.

These rules cover only what ruff cannot. Anything ruff already enforces and auto-fixes under `select = ["ALL"]` —
argument-count caps (`PLR0913`), `TYPE_CHECKING` import moves (`TC00x`), modern-syntax upgrades (`UP`),
exception-message/`raise ... from` hygiene (`EM`/`B904`), blind-except bans (`BLE001`/`E722`) — is handled by the lint
step above and must not be restated here.

### Code rules

1. **Comments and docstrings explain why, not what — concisely.** Delete any comment or docstring that restates what the
   code does. Keep only those giving rationale the code can't show, and keep them as short as possible — code should be
   self-documenting. Where the *why* is genuinely non-obvious (a workaround, a subtle constraint, a non-local decision),
   a short comment is encouraged rather than omitted: it captures rationale the code cannot, and doubles as durable
   context a coding agent will reliably read.

1. **No section/grouping comments.** Never use a comment as a visual divider or section header to group code
   (`# --- section a ---`, `# === helpers ===`, `# Setup`, banner bars). It restates structure the code already shows
   and rots as code moves. If a block feels like it needs a label, that is a signal to extract a function or class with
   a descriptive name instead.

1. **Wrap to the configured line length.** Use the project's ruff `line-length` (`pyproject.toml`/`ruff.toml`; 120 if
   unset) for everything. `ruff format` already wraps code; manually reflow long comments and docstrings to the same
   width — ruff does not touch prose. No line should exceed the limit.

1. **Compact, late variables.** Define each variable as late as possible, immediately before its first use — not at the
   top of a block. Strongly prefer inlining single-use values at their point of use: a variable earns its name only when
   its value is used in two or more places, or when naming it genuinely makes the code more compact (e.g. it untangles a
   deeply nested expression instead of repeating it) without hurting readability.

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

1. **No defensive code for impossible states.** Don't guard against a condition the callers, types, or invariants
   already preclude — delete the branch instead of writing an `if` (or a test) for a case that cannot occur. A guard
   earns its place only when something real can violate it at runtime (untrusted input, an allocation/OS failure, a
   documented `None`). If a branch is unreachable without a bug elsewhere it is dead code: remove it, or — when removing
   it would lose a genuinely-untestable safety net (an allocation failure, an exhaustive-`switch` default the compiler
   requires) — exclude it from coverage with a one-line justification, never a hollow test.

### Test rules

1. **Parameterize.** Collapse near-duplicate test functions into a single `@pytest.mark.parametrize` using
   `pytest.param(..., id="...")` for each case. Always give a readable `id`.

1. **Fixtures over setup duplication.** Extract repeated setup/teardown into fixtures.

1. **No test classes — fold the grouping into the name.** Never group tests with a class. Use module-level test
   functions and move what would have been the class name into a prefix on each test's name (`class TestParser` with
   `test_handles_empty` → `test_parser_handles_empty`). When a group grows large, split it into a separate test
   file/module rather than a class.

1. **100% diff coverage.** Every line changed in the PR must be covered by tests, measured against the diff versus the
   merge base (not whole-repo coverage). Add tests for any uncovered changed line before the PR is ready.

1. **Test through public APIs only.** Exercise behavior via the module's public interface; never import, call, or assert
   on private (underscore-prefixed) functions, methods, or attributes directly. If private logic needs coverage, drive
   it through the public entry point that uses it. Never widen a symbol's visibility — dropping its underscore prefix
   (`_is_machine_reachable` → `is_machine_reachable`) or adding it to `__all__` — just to make it testable; that is
   cheating and not allowed. Cover it through the public caller instead.

1. **Mock only true boundaries; never hand-roll fakes.** Exercise real collaborators by default. Reach for a mock only
   at a genuine seam you cannot run in-process — network, clock, filesystem, subprocess. Prefer `pytest-mock`'s `mocker`
   fixture; only fall back to stdlib `unittest.mock` when `mocker` isn't available (e.g. code outside a test where the
   fixture can't be injected). Never write a bespoke fake/stub class. When a real class/function exists to spec against,
   prefer `create_autospec(Target)` over a raw mock so the mock keeps the real signature and fails when the API drifts;
   fall back to a plain `MagicMock` only when there is nothing to spec. Build mocks compactly by passing
   attributes/return values to the constructor — `mocker.MagicMock(name="x", total=3)` — rather than defining the mock
   and then assigning fields line by line. A test built mostly of mocks asserting mock calls tests the mock, not the
   code — prefer one integration test through the real path.

1. **Every test must be able to fail for the right reason.** Breaking the behavior a test targets must make that test
   fail; reaching a line or branch is not the same as testing it, and a test that passes regardless is as empty as no
   test at all. Two ways tests fall short:

   - *Tautological assertions* — `assert True`, asserting a literal that was just passed in, or asserting only that a
     mock was called without checking the resulting value or state. If the test would still pass with the function body
     replaced by `pass`/`raise`, it tests nothing.
   - *Coverage without discrimination* — executing a branch only to satisfy the coverage gate while asserting something
     that holds whether or not that branch fired: an idempotence or round-trip check (`f(f(x)) == f(x)`,
     `parse(render(x)) == x`) that still passes on a no-op, a "does not raise" / truthy assertion (`assert parse(src)`,
     `assert result`), or a differential that passes regardless. Pin the observable difference *that* branch produces —
     the exact output, the specific value, the state change.

   When a path has no observable effect to assert (a defensive guard, an unreachable-without-a-bug invariant), do not
   manufacture a hollow test — delete it or exclude it per *No defensive code for impossible states*.

Keep all other house conventions (type annotations everywhere, one assertion-concept per test) intact while applying
these.
