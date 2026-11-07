# Simp: Python rules

These add the Python-only mechanics; apply them alongside the Common rules.

After editing, fix linting before the PR is opened. If the project has a `.lintrc.yaml` at its root, run
`linterator check -l info --fix .` (linterator already runs ruff, so do not also run it separately). Otherwise, run
`ruff format .; ruff check --fix --unsafe-fixes --output-format=concise .`. Either way, ensure it passes.

These rules cover only what ruff cannot. The lint step above handles anything ruff already enforces and auto-fixes under
`select = ["ALL"]`, so these rules must not restate it: argument-count caps (`PLR0913`), `TYPE_CHECKING` import moves
(`TC00x`), modern-syntax upgrades (`UP`), exception-message/`raise ... from` hygiene (`EM`/`B904`), and blind-except
bans (`BLE001`/`E722`).

01. **Walrus.** Use `:=` whenever it makes the code more compact without hurting readability or breaking the density cap
    of Common rule 04.

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
