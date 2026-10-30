---
name: simp
description: Simplify and tighten code and tests to a strict house style (concise why-not-what comments, parameterized tests, explicit exports, late/compact definitions, idiomatic typing). Common rules apply to every language; the Python section adds Python-only mechanics. Use when asked to simplify, tidy, or refactor for style, not to find bugs.
---

# Simp

Apply the rules below to the files in scope (the current diff, a named file, or the file under discussion). This is a
quality pass: simplify and restyle without changing what the code computes. A few rules change behavior at the edges:
dropping an unused default changes a signature, narrowing an `except` lets an unlisted error propagate, and removing a
dependency fallback turns a degraded mode into a load-time failure. Name each such change in the report. It does not
hunt for bugs; use `/code-review` for that.

Read each target file and its siblings first to match existing conventions, then apply every rule that fits. Report what
changed and why. Run the project's tests if test files were touched.

Apply the rules as written. A rule's exception holds only when a concrete, unavoidable necessity forces it: a line that
cannot otherwise fit the width limit, a value the language requires to exist before use, an upstream bug with no other
fix. "It reads nicer", "it documents intent", "it keeps things symmetric", "it is more consistent", and anything phrased
as "could" or "I think" are not exceptions; when that is the only justification, the rule wins. Do not invent a reason
to keep a violation.

## Structural refactors: propose, then wait

Apply the rules below directly while the change stays inside one module. A change that crosses module boundaries (moving
code, a responsibility or a value between modules, removing an interface other modules name, reversing a dependency) is
a structural refactor: propose it, and touch code only after the user agrees. Look for one when the change in scope has
made the code harder to manage, for example:

- a module or class now mixes concerns that belong apart (I/O inside domain logic, one component's details hard-coded in
  a generic one);
- a dependency now points the wrong way (a lower layer importing a higher one, a cycle);
- logic is duplicated across places that will drift;
- a function or class has grown past one responsibility, or a seam exists only to make testing possible;
- a package no longer groups related concepts, so a reader cannot tell where something lives.

After the style pass, list each proposal with what moves where, why it improves separation of concerns, readability or
maintainability, and what it touches. Rank them by payoff, apply none of them, and ask which to do. Implement only the
ones the user accepts.

The **Common** rules apply to every language. They are written with Python examples and tools (`ruff`, `pytest`,
`Final`), but the rule itself is language-agnostic: in another language apply the same intent with that language's
idioms, mapping the Python specifics yourself (its formatter for `ruff`, its test framework for `pytest`). The
**Python** section adds the mechanics that only make sense in Python; when working in Python, apply both.

## Common

### Code rules

01. **Comments and docstrings explain why, not what, concisely.** Delete any comment or docstring that restates what the
    code does. Keep only those giving rationale the code can't show, and keep them as short as possible; code should be
    self-documenting.

    Where the *why* is non-obvious (a workaround, a subtle constraint, a non-local decision), a short comment is
    encouraged rather than omitted: it captures rationale the code cannot, and doubles as durable context a coding agent
    will reliably read. Put that comment at the line that makes the choice.

    Keep every paragraph of a comment, docstring or document under 100 words; split a longer one at a change of topic.
    In documents (README, design notes), prefer paragraphs, distill parallel items into a short list, and use **bold**,
    *italics*, `>` quotes and indentation where they make the text easier to read; give a long document headings for its
    main topics.

    A README describes the product from its user's side. A contributing guide introduces the domain concepts and how
    they relate, illustrated by one labeled example; it names no classes, modules or files (they rot) and skips generic
    language tooling. Link each external repo, service, tool or standard at its first mention, put later mentions in
    backticks (`` `Redis` ``), and spell a project by its published name (`requests-oauthlib`, not the import name
    `requests_oauthlib`).

    Docstrings follow the same rules:

    - A module or package docstring is one line saying what the module is: no design notes, usage instructions or import
      advice. Test modules carry none.
    - Classes, functions and methods carry none; their name, signature and types document them, and a class's why goes
      in a comment at the code it explains. Two exceptions document every parameter, the return value and each exception
      callers must handle (Python: reST `:param:`, `:returns:`, `:raises:`): a library's public, user-facing API, and a
      method of a public interface (protocol, ABC) whose name does not say what it does or that callers must expect to
      raise. A project that follows this disables ruff's missing-docstring rules (`D1xx`) in its configuration; that is
      a project setting, not a suppression.

02. **No section/grouping comments.** Never use a comment as a visual divider or section header to group code
    (`# --- section a ---`, `# === helpers ===`, `# Setup`, banner bars). It restates structure the code already shows
    and rots as code moves. If a block feels like it needs a label, that is a signal to extract a function or class with
    a descriptive name instead.

03. **Wrap to the configured line length.** Use the project's configured width: in Python, ruff's `line-length`
    (`pyproject.toml`/`ruff.toml`; 120 if unset). The formatter wraps code; manually reflow comments, docstrings and
    documentation to the same width, since formatters do not touch prose. No line should exceed the limit.

04. **Compact, late variables.** Define each variable as late as possible, immediately before its first use, not at the
    top of a block. Inline single-use local values at their point of use. A local earns a name when its value is used in
    two or more places, or when naming it makes the code more compact, most often because inlining would wrap the
    statement across several lines (a long log or exception message, a nested call argument), or because the identical
    subexpression repeats within one statement. Prefer the named two-line form over the inlined multi-line explosion.

    Readability, documenting intent, visual symmetry, and giving a comment a home are not exceptions: inline the value
    and put any comment at the use site. A genuine module-scope configuration or taxonomy constant stays named (and
    typed `Final` in Python); lifting a one-off local to module scope only to name or comment it does not make it one.
    The same holds for fields: keep the object that owns a value and read through it (`self._engine.capabilities`),
    never copy its attributes into fields of your own.

05. **Module scope only for shared values.** A module-level constant or variable belongs at module scope only when two
    or more functions or methods use it, or another module imports it (check every consumer, including sibling repos in
    scope). A value used by one function moves into it, and is inlined there when used once.

    Values the language or framework needs at module scope (decorator and default arguments, class bodies, exports, type
    aliases, test markers) stay, as do values whose identity must stay stable across calls (a memoization key, a UI hook
    dependency) and a value expensive to rebuild on a hot path, with a one-line comment saying so.

06. **Descriptive names.** Give every name a descriptive word. Single-character names are allowed only as loop or
    comprehension targets (`[x.id for x in rows]`); everywhere else name the thing. Avoid architecture jargon whose
    everyday meaning differs (`WorkerPorts` for a group of storage collaborators reads as network ports): name the thing
    for what it holds. One name per concept, one concept per name: two concepts never share a name (two modules called
    `queue`, "sealed" meaning both encrypted and inventory-complete), and one concept is never called two things.

07. **Define after use (reads like a book).** Order every module so each function, method, and class is defined *below*
    the code that uses it: the entry point sits near the top and the helpers it calls follow in first-call order, so the
    file reads top-to-bottom like prose.

    The order is depth-first: a callee sits directly after the caller that first references it, before that caller's
    next sibling, whether it is public or private (never group private helpers at the bottom). A private module-level
    helper used by one class becomes a method of it (static when it needs no state) so it can sit after its caller. The
    only exceptions are genuine runtime ordering requirements: a name that must already exist when a line *executes* (a
    module-scope value, a decorator, a default argument, a base class).

08. **Functions separate tasks or share code.** A function exists to name a distinct task or to reuse code, not to cut a
    body into pieces. As guidance, not a rule, bodies read best at 20 to 40 lines; a shorter body is fine, as is a
    longer one when splitting would cut through one task.

    Inline a private helper with a single caller unless it is a distinct task that reads better on its own or it is
    passed as a callback (a thread target, a signal handler, a `key=`). A function whose body only forwards to a
    constructor or another call is inlined at every caller, making the target public if needed, unless it implements an
    interface or is passed as a callback. Split a long function only at a task boundary, never into one-use fragments to
    meet a line count.

09. **Group values that travel together.** Parameters that describe one thing or always move together become one
    immutable record passed as a single argument; review every signature with five or more parameters. Group by meaning,
    not to hit a count, and leave a parameter alone when no group fits. Leave a dependency's own signature as it is.

10. **No unused defaults.** A parameter or field default stays only when some production call site omits it on purpose.
    Otherwise remove it so callers pass the value explicitly; tests do not justify a default. A command-line tool's
    user-facing defaults stay.

11. **Remove what production code does not use.** That covers functions, methods, fields, parameters, return values and
    branches no production code reads. A parameter that exists only so tests can inject a stand-in goes too; tests patch
    the real boundary instead.

12. **Interfaces need a second implementation or a layer to decouple.** Within one module, apply this directly; across
    modules, propose it. Remove an interface (protocol, ABC) with one implementation in the same package; its consumers
    name the implementation. An interface that does decouple layers lives with the code that consumes it, not in a
    shared "interfaces" module, and each implementation inherits it explicitly so the type checker verifies it where it
    is defined (a narrow private view several classes satisfy may stay structural).

    A resource with paired setup and teardown (signal handlers, a lock, a temporary install) is a context manager, so
    the teardown cannot be forgotten.

13. **Keep details with their owner.** Moving a value or type to another module is a structural refactor, so propose it.
    A value specific to one component (its lease duration, its capacity, a feed name) is declared by that component and
    read through its interface, never hard-coded in a generic module with a comment naming the component.

    A type lives with the logic that builds and operates on it, not in a shared `model` or `types` package: one used by
    a single concept moves to it, one shared by several goes to the owner of the contract they meet at, and packages
    never import each other at runtime (annotation-only references go under `TYPE_CHECKING`).

14. **Explicit errors.** Catch only the exception types the guarded call can raise; read the callee to find them. A
    catch-all is allowed only at a deliberate containment boundary (a service loop's per-cycle or per-item handler),
    with a one-line reason. Define a new error type only when some handler must treat it differently from an existing
    type; otherwise raise a built-in one. Never tell errors apart by reading their message.

15. **No fallbacks for required dependencies.** Load a required dependency directly and let a broken install fail at
    load time. Do not wrap its import in a guard that turns its absence into a friendly refusal or a degraded mode.

16. **No defensive code for impossible states.** Don't guard against a condition the callers, types, or invariants
    already preclude; delete the branch instead of writing an `if` (or a test) for a case that cannot occur. A guard
    earns its place only when something real can violate it at runtime (untrusted input, an allocation/OS failure, a
    documented `None`).

    If a branch is unreachable without a bug elsewhere it is dead code: remove it, or, when removing it would lose an
    untestable safety net (an allocation failure, an exhaustive-`switch` default the compiler requires), exclude it from
    coverage with a one-line justification, never a hollow test.

17. **Compare composite values in one check.** When comparing or asserting a structured value (`dict`, `list`, `tuple`,
    dataclass, model), compare the whole object with a single `==` against one expected literal rather than picking it
    apart field by field across several comparisons. One equality reads better, gives a full diff on failure, and can't
    drift out of sync. Break it up only when you assert on a subset.

18. **Fix, never suppress, linter and type-checker findings.** Resolve every finding by fixing the code. Do not add
    ignore directives or disable rules to silence them. When a genuine fix is impossible (e.g. an upstream stub bug),
    the suppression names the specific error code and carries an inline reason or upstream link, never a blanket ignore.

19. **Explicit public API.** Expose only the names other modules use; keep everything else internal to the file. Never
    widen a symbol's visibility just to reach it from elsewhere.

### Test rules

1. **Mirror source paths in tests.** Put a source file's tests at the corresponding path under the test root:
   `src/a/x.py` maps to `tests/unit/a/test_x.py` (and `tests/integration/a/test_x.py` for tests that need a real backing
   service). When changing existing source, extend its existing test file; create a new test file only when adding its
   source file.

2. **One behavior per test.** Each test checks one thing. Split a test that asserts unrelated behaviors; a precondition
   assert followed by the result it guards is still one behavior. No branching (`if`) inside a test body: parameterize
   instead.

3. **Parameterize.** Collapse near-duplicate test functions into a single table-driven case with a readable id per row.

4. **Shared setup over duplication.** Extract repeated setup/teardown into shared fixtures, and prefer injecting a
   fixture over calling a helper method wherever a fixture fits.

5. **100% diff coverage.** Every line changed in the PR must be covered by tests, measured against the diff versus the
   merge base (not whole-repo coverage). Add tests for any uncovered changed line before the PR is ready.

6. **Test through public APIs only.** Exercise behavior via the module's public interface; never import, call, or assert
   on private (underscore-prefixed) functions, methods, or attributes directly. If private logic needs coverage, drive
   it through the public entry point that uses it. Never widen a symbol's visibility just to make it testable; cover it
   through the public caller instead.

7. **Mock only true boundaries; never hand-roll fakes.** Exercise real collaborators by default. Reach for a mock only
   at a genuine seam you cannot run in-process: network, clock, filesystem, subprocess. Prefer a spec-bound mock that
   tracks the real signature over a free-form one, and build it compactly. Never sleep to let a thread run: wait on an
   event the mock sets. A test built mostly of mocks asserting mock calls tests the mock, not the code; prefer one
   integration test through the real path.

8. **Every test must be able to fail for the right reason.** Breaking the behavior a test targets must make that test
   fail; reaching a line or branch is not the same as testing it, and a test that passes regardless is as empty as no
   test at all. Two ways tests fall short:

   - *Tautological assertions*: `assert True`, asserting a literal that was just passed in, or asserting only that a
     mock was called without checking the resulting value or state. If the test would still pass with the function body
     replaced by `pass`/`raise`, it tests nothing.
   - *Coverage without discrimination*: executing a branch only to satisfy the coverage gate while asserting something
     that holds whether or not that branch fired: an idempotence or round-trip check that still passes on a no-op, a
     "does not raise" / truthy assertion, or a differential that passes regardless. Pin the observable difference *that*
     branch produces: the exact output, the specific value, the state change.

   When a path has no observable effect to assert (a defensive guard, an unreachable-without-a-bug invariant), do not
   manufacture a hollow test; delete it or exclude it per *No defensive code for impossible states*.

## Python

These add the Python-only mechanics; apply them alongside the Common rules.

After editing, fix linting before the PR is opened. If the project has a `.lintrc.yaml` at its root, run
`linterator check -l info --fix .` (linterator already runs ruff, so do not also run it separately). Otherwise, run
`ruff format .; ruff check --fix --unsafe-fixes --output-format=concise .`. Either way, ensure it passes.

These rules cover only what ruff cannot. The lint step above handles anything ruff already enforces and auto-fixes under
`select = ["ALL"]`, so these rules must not restate it: argument-count caps (`PLR0913`), `TYPE_CHECKING` import moves
(`TC00x`), modern-syntax upgrades (`UP`), exception-message/`raise ... from` hygiene (`EM`/`B904`), and blind-except
bans (`BLE001`/`E722`).

01. **Walrus.** Use `:=` whenever it makes the code more compact without hurting readability.

02. **`Final` for constants.** Any value that is never reassigned, especially at module scope, is typed `Final[<type>]`.

03. **Global naming.** Module-scope variables are `UPPER_CASE`, also `_`-prefixed when not imported by another
    business-logic module (e.g. `_DEFAULT_TIMEOUT: Final[int] = 30`, `_LOGGER: Final[logging.Logger] = ...`).

04. **Explicit exports.** Every name imported by other modules appears in an `__all__ = [...]` at the end of the file.

05. **Precise types.** Annotate all code, tests included. Never reach for `Any`, `object`, `cast()`, `Callable[..., X]`
    or `# type: ignore`.

    - A record only this code builds and reads is a dataclass (Python rule 08). A `TypedDict` (`NotRequired` for
      optional keys) is for a dict at a boundary, such as a wire payload as received or a library's dict argument; parse
      it into a dataclass before it travels further. Arbitrary JSON is a recursive alias,
      `type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]`. Reuse a dependency's
      alias when it has one.
    - Untyped input (`json.loads`, an HTTP body, a dynamic import) is validated once at the boundary with `TypeIs` or
      isinstance checks that narrow it, not cast. The guard's own parameter is the one place `object` belongs:
      `def is_json(value: object) -> TypeIs[JsonValue]`.
    - A callable parameter with a real signature is a `Protocol`; parse command-line options into a typed
      `argparse.Namespace` subclass (`parse_args(argv, namespace=Options())`), never through `vars()`.
    - An unavoidable suppression names the specific code, never a blanket `# ty: ignore` / `# type: ignore`, and carries
      a reason or link, e.g. `# ty: ignore[no-matching-overload]  # https://github.com/astral-sh/ty/issues/2428`.

06. **Define-after-use caveat.** Type annotations are not a use: `from __future__ import annotations` (≤3.13) and PEP
    649 lazy evaluation (3.14+) defer them, so never reorder a definition to satisfy an annotation reference. When the
    project targets 3.14 or later, do not add the `__future__` import; remove it where present.

07. **Imports.** Import from the same package or a package below it relatively (`from . import session`,
    `from .settings import WorkerConfig`); import up or across absolutely (`from mypkg.model.work import WorkItem`).
    Import the class, function or constant itself rather than its module (`from .findings import DbWriter`, not
    `findings.DbWriter`), unless names clash, a test patches the attribute on the module, or the module is the idiom
    (`datetime`, `json`). A package `__init__.py` holds only its docstring: no re-exports and no empty `__all__`.

08. **Records.** A dataclass is `@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)`. Mutable state that must
    move belongs on the object that owns the change, not on a shared record.

09. **Strings.** Build text with f-strings, never with `+` (bytes have no f-string form and may concatenate).

10. **No test classes.** Never group tests in a class. Fold what would have been the class name into a prefix on each
    test function's name (`class TestParser` with `test_handles_empty` → `test_parser_handles_empty`), and prefer
    multiple test files over large groupings.

11. **Pytest mechanics.** Parameterize with `@pytest.mark.parametrize` using `pytest.param(..., id="...")`; put shared
    setup in `pytest` fixtures; mock through `pytest-mock`'s `mocker` (stdlib `unittest.mock` only when the fixture is
    unavailable, never a bespoke fake class), prefer `mocker.create_autospec(Target)` over a raw mock (for a bare
    callable, autospec a typed stub function), and build mocks via constructor kwargs
    (`mocker.MagicMock(name="x", total=3)`) rather than define-then-assign.

Keep all other house conventions (type annotations everywhere, one assertion-concept per test) intact while applying
these.
