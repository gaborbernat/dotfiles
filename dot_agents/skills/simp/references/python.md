# Simp: Python rules

These add the Python-only mechanics; apply them alongside the Common rules.

After editing, fix linting before the PR is opened. If the project has a `.lintrc.yaml` at its root, run
`linterator check -l info --fix .` (linterator already runs ruff, so do not also run it separately). Otherwise, run
`ruff check --fix --unsafe-fixes --output-format=concise . && uvx simplint check --fix . && ruff format .`, in that
order: simplint sits between Ruff's linter and its formatter. Either way, ensure it passes.

[simplint](https://github.com/gaborbernat/simplint) is the source of truth for the Python style it checks; where this
skill and simplint disagree, simplint wins. It enforces, and these rules therefore do not restate: section and restating
comments, comment and docstring paragraph length, docstrings outside a library's public API, definition order and class
member order, single-use locals and constants, walrus candidates, single-caller and forwarding helpers, unused defaults,
code and exports, message matching, needless error classes, import fallbacks, unexplained suppressions, `__all__`,
`Final` and module-variable naming, `__future__` annotations, import style, package `__init__.py` content, dataclass
options, string concatenation, test classes, parametrize ids, branching and loops in tests, mocks without a spec or with
attributes set after creation, `unittest.mock`, sleeping in tests, and constant asserts. Ruff, under `select = ["ALL"]`,
covers argument-count caps, `TYPE_CHECKING` moves, syntax upgrades, exception-message hygiene and blind excepts.

1. **Precise types.** Annotate all code, tests included. Never reach for `Any`, `object`, `cast()`, `Callable[..., X]`
   or `# type: ignore`.

   - A record only this code builds and reads is a dataclass. A `TypedDict` (`NotRequired` for optional keys) is for a
     dict at a boundary, such as a wire payload as received or a library's dict argument; parse it into a dataclass
     before it travels further. Arbitrary JSON is a recursive alias,
     `type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]`. Reuse a dependency's
     alias when it has one.
   - Untyped input (`json.loads`, an HTTP body, a dynamic import) is validated once at the boundary with `TypeIs` or
     isinstance checks that narrow it, not cast. The guard's own parameter is the one place `object` belongs:
     `def is_json(value: object) -> TypeIs[JsonValue]`.
   - A callable parameter with a real signature is a `Protocol`; parse command-line options into a typed
     `argparse.Namespace` subclass (`parse_args(argv, namespace=Options())`).
   - An unavoidable suppression names the specific code, never a blanket `# ty: ignore` / `# type: ignore`, and carries
     a reason or link, e.g. `# ty: ignore[no-matching-overload]  # https://github.com/astral-sh/ty/issues/2428`.

2. **Records.** Mutable state that must move belongs on the object that owns the change, not on a shared record.

3. **Pytest mechanics.** Put shared setup in `pytest` fixtures and mock through `pytest-mock`'s `mocker`, preferring
   `mocker.create_autospec(Target)`; for a bare callable, autospec a typed stub function.

Keep all other house conventions (type annotations everywhere, one assertion-concept per test) intact while applying
these.
