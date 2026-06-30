---
name: simp
description: Simplify and tighten code and tests to a strict house style — concise why-not-what comments, parameterized tests, explicit exports, late/compact definitions, idiomatic typing. Common rules apply to every language; the Python section adds Python-only mechanics. Use when asked to simplify, tidy, or refactor for style — not to find bugs.
---

Apply the rules below to the files in scope (the current diff, a named file, or the file under discussion). This is a
quality pass: simplify and restyle without changing behavior. It does not hunt for bugs — use `/code-review` for that.

Read each target file and its siblings first to match existing conventions, then apply every rule that fits. Report what
changed and why. Run the project's tests if test files were touched.

Apply the rules as written. A rule's exception holds only when a concrete, unavoidable necessity forces it — a line that
cannot otherwise fit the width limit, a value the language requires to exist before use, an upstream bug with no other
fix. "It reads nicer", "it documents intent", "it keeps things symmetric", "it is more consistent", and anything phrased
as "could" or "I think" are not exceptions; when that is the only justification, the rule wins. Do not invent a reason
to keep a violation.

The **Common** rules apply to every language. They are written with Python examples and tools (`ruff`, `pytest`,
`Final`), but the rule itself is language-agnostic: in another language apply the same intent with that language's
idioms, mapping the Python specifics yourself (its formatter for `ruff`, its test framework for `pytest`). The
**Python** section adds the mechanics that only make sense in Python; when working in Python, apply both.

## Common

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

1. **Wrap to the configured line length.** Use the project's configured width — in Python, ruff's `line-length`
   (`pyproject.toml`/`ruff.toml`; 120 if unset). The formatter wraps code; manually reflow long comments and docstrings
   to the same width, since formatters do not touch prose. No line should exceed the limit.

1. **Compact, late variables.** Define each variable as late as possible, immediately before its first use — not at the
   top of a block. Inline single-use local values at their point of use. A local earns a name when its value is used in
   two or more places, or when naming it makes the code more compact — most often because inlining would wrap the
   statement across several lines (a long log or exception message, a nested call argument), or because the identical
   subexpression repeats within one statement. Prefer the named two-line form over the inlined multi-line explosion.
   Readability, documenting intent, visual symmetry, and giving a comment a home are not exceptions — inline the value
   and put any comment at the use site. A genuine module-scope configuration or taxonomy constant stays named (and typed
   `Final` in Python); lifting a one-off local to module scope only to name or comment it does not make it one.

1. **Descriptive names.** Give every name a descriptive word. Single-character names are allowed only as loop or
   comprehension targets (`[x.id for x in rows]`); everywhere else name the thing.

1. **Define after use (reads like a book).** Order every module so each function, method, and class is defined *below*
   the code that uses it: the entry point sits near the top and the helpers it calls follow in first-call order, so the
   file reads top-to-bottom like prose. The only exceptions are genuine runtime ordering requirements — a name that must
   already exist when a line *executes* (a module-scope value, a decorator, a default argument, a base class).

1. **No defensive code for impossible states.** Don't guard against a condition the callers, types, or invariants
   already preclude — delete the branch instead of writing an `if` (or a test) for a case that cannot occur. A guard
   earns its place only when something real can violate it at runtime (untrusted input, an allocation/OS failure, a
   documented `None`). If a branch is unreachable without a bug elsewhere it is dead code: remove it, or — when removing
   it would lose a genuinely-untestable safety net (an allocation failure, an exhaustive-`switch` default the compiler
   requires) — exclude it from coverage with a one-line justification, never a hollow test.

1. **Compare composite values in one check.** When comparing or asserting a structured value (`dict`, `list`, `tuple`,
   dataclass, model), compare the whole object with a single `==` against one expected literal rather than picking it
   apart field by field across several comparisons. One equality reads better, gives a full diff on failure, and can't
   drift out of sync. Break it up only when you genuinely assert on a subset.

1. **Fix, never suppress, linter and type-checker findings.** Resolve every finding by fixing the code. Do not add
   ignore directives or disable rules to silence them. When a genuine fix is impossible (e.g. an upstream stub bug), the
   suppression names the specific error code and carries an inline reason or upstream link — never a blanket ignore.

1. **Explicit public API.** Expose only the names other modules use; keep everything else internal to the file. Never
   widen a symbol's visibility just to reach it from elsewhere.

### Test rules

1. **Parameterize.** Collapse near-duplicate test functions into a single table-driven case with a readable id per row.

1. **Shared setup over duplication.** Extract repeated setup/teardown into shared fixtures, and prefer injecting a
   fixture over calling a helper method wherever a fixture fits.

1. **100% diff coverage.** Every line changed in the PR must be covered by tests, measured against the diff versus the
   merge base (not whole-repo coverage). Add tests for any uncovered changed line before the PR is ready.

1. **Test through public APIs only.** Exercise behavior via the module's public interface; never import, call, or assert
   on private (underscore-prefixed) functions, methods, or attributes directly. If private logic needs coverage, drive
   it through the public entry point that uses it. Never widen a symbol's visibility just to make it testable; cover it
   through the public caller instead.

1. **Mock only true boundaries; never hand-roll fakes.** Exercise real collaborators by default. Reach for a mock only
   at a genuine seam you cannot run in-process — network, clock, filesystem, subprocess. Prefer a spec-bound mock that
   tracks the real signature over a free-form one, and build it compactly. A test built mostly of mocks asserting mock
   calls tests the mock, not the code — prefer one integration test through the real path.

1. **Every test must be able to fail for the right reason.** Breaking the behavior a test targets must make that test
   fail; reaching a line or branch is not the same as testing it, and a test that passes regardless is as empty as no
   test at all. Two ways tests fall short:

   - *Tautological assertions* — `assert True`, asserting a literal that was just passed in, or asserting only that a
     mock was called without checking the resulting value or state. If the test would still pass with the function body
     replaced by `pass`/`raise`, it tests nothing.
   - *Coverage without discrimination* — executing a branch only to satisfy the coverage gate while asserting something
     that holds whether or not that branch fired: an idempotence or round-trip check that still passes on a no-op, a
     "does not raise" / truthy assertion, or a differential that passes regardless. Pin the observable difference *that*
     branch produces — the exact output, the specific value, the state change.

   When a path has no observable effect to assert (a defensive guard, an unreachable-without-a-bug invariant), do not
   manufacture a hollow test — delete it or exclude it per *No defensive code for impossible states*.

## Python

These add the Python-only mechanics; apply them alongside the Common rules.

After editing, fix linting before the PR is opened. If the project has a `.lintrc.yaml` at its root, run
`linterator check -l info --fix .` (linterator already runs ruff, so do not also run it separately). Otherwise, run
`ruff format .; ruff check . --fix --unsafe-fixes . --output-format=concise`. Either way, ensure it passes.

These rules cover only what ruff cannot. Anything ruff already enforces and auto-fixes under `select = ["ALL"]` —
argument-count caps (`PLR0913`), `TYPE_CHECKING` import moves (`TC00x`), modern-syntax upgrades (`UP`),
exception-message/`raise ... from` hygiene (`EM`/`B904`), blind-except bans (`BLE001`/`E722`) — is handled by the lint
step above and must not be restated here.

1. **Walrus.** Use `:=` whenever it makes the code more compact without hurting readability.

1. **`Final` for constants.** Any value that is never reassigned, especially at module scope, is typed `Final[<type>]`.

1. **Global naming.** Module-scope variables are `UPPER_CASE`, additionally `_`-prefixed when not imported by another
   business-logic module (e.g. `_DEFAULT_TIMEOUT: Final[int] = 30`, `_LOGGER: Final[logging.Logger] = ...`).

1. **Explicit exports.** Every name imported by other modules appears in an `__all__ = [...]` at the end of the file.

1. **Type suppression.** Never reach for `Any`, `object`, or `# type: ignore`. An unavoidable suppression names the
   specific code, never a blanket `# ty: ignore` / `# type: ignore`, and carries a reason or link, e.g.
   `# ty: ignore[no-matching-overload]  # https://github.com/astral-sh/ty/issues/2428`.

1. **Define-after-use caveat.** Type annotations are not a use: `from __future__ import annotations` (≤3.13) and PEP 649
   lazy evaluation (3.14+) defer them, so never reorder a definition to satisfy an annotation reference.

1. **No test classes.** Never group tests in a class. Fold what would have been the class name into a prefix on each
   test function's name (`class TestParser` with `test_handles_empty` → `test_parser_handles_empty`), and prefer
   multiple test files over large groupings.

1. **Pytest mechanics.** Parameterize with `@pytest.mark.parametrize` using `pytest.param(..., id="...")`; put shared
   setup in `pytest` fixtures; mock through `pytest-mock`'s `mocker` (stdlib `unittest.mock` only when the fixture is
   unavailable, never a bespoke fake class), prefer `mocker.create_autospec(Target)` over a raw mock, and build mocks
   via constructor kwargs (`mocker.MagicMock(name="x", total=3)`) rather than define-then-assign.

Keep all other house conventions (type annotations everywhere, one assertion-concept per test) intact while applying
these.
