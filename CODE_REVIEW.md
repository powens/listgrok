# Code Review Findings

## `army_list.py`

- **Trivial `add_*` wrappers** (lines 15, 48, 83): `add_wargear`, `add_model_set`, and `add_unit` wrap single `dict`/`list` operations with no validation or transformation. Callers can operate on the collections directly.

## `parse_list.py`

- **Commented-out dead code** (lines 8–13): The entire try/except fallback is commented out, making this function an alias for `parse_official_app`. Either implement the fallback or remove the dead code.
- **`list` shadows the built-in** (line 7): `def parse_list(list: str)` — `list` is a Python built-in. Rename the parameter to `list_text` for consistency with how tests refer to it.

## `official_app.py`

- **Duplicate compiled regex** (lines 8–11): `POINTS_LABEL_REGEX` and `POINTS_LABEL_REGEX_DOTALL` are identical patterns differing only by a flag. Use one definition and pass `re.DOTALL` at the call site, or compile a single pattern with the flag included.
- **`_is_army_size_line` is dead code** (line 25): Defined and tested but never called within the parser logic. Either use it or remove it.
- **Fragile single-vs-multi-model detection** (lines 118–122): Detection via `max(count_leading_spaces(...))` relies on exact whitespace layout of the export format. A single upstream formatting change silently misclassifies units. Checking for the presence of `"• "` at the top level and `"◦ "` nested beneath it would be more robust.
- **Large block of commented-out code** (lines 182–249): ~70 lines of old implementation left behind. Delete it — git history preserves it if needed.
- **`_handle_unit_line` receives `uc` it may not use** (line 58): When the line is `"Warlord"` or starts with `"Enhancements: "`, the `uc: UnitComposition` parameter is ignored. This creates an unclear contract and forces callers to pass a dummy `uc` even when irrelevant.
- **Bullet stripping done in two places** (lines 60, 96–108): `_populate_multi_model_unit` checks `line.startswith("• ")` then routes, while `_handle_unit_line` also strips bullets via `re.sub`. The stripping logic is split and inconsistent across both functions.

## `new_recruit_gw.py`

- **`lstrip("• ")` is a bug** (line 39): `str.lstrip` strips individual *characters* from a set, not the prefix as a whole. Use `removeprefix("• ")` consistently, as `official_app.py` does.
- **Parser state stored as instance attributes** (lines 114–119): `self.list`, `self.state_machine`, `self.last_unit_type`, and `self.line_collection` are all set inside `parse()`, making the parser stateful and non-reusable. Move state to local variables or a dedicated `ParserState` dataclass as `official_app.py` does.
- **State machine uses magic strings instead of an Enum** (line 117): `official_app.py` uses `ParserStateMachine(Enum)` while this file uses plain strings `"HEADER"`, `"UNIT"`. Strings give no IDE support or typo safety.
- **Magic numbers for leading spaces** (lines 80, 87, 102–107): `0`, `2`, and `4` spaces are compared against with no named constants. `official_app.py` at least defines `LEADING_SPACES_FOR_SINGLE_MODEL_UNIT = 2`.
- **`max()` written as a manual loop** (lines 64–68): Replace the manual accumulation loop with `max(count_leading_spaces(line) for line in lines)`.

## `new_recruit.py`

- **Incomplete, abandoned parallel implementation**: `_handle_unit` is a `pass` stub, `_handle_configuration` is defined but never called, and `ARMY_ROSTER_BLOCK`, `UNIT_BLOCK`, and `SINGLE_UNIT` regex constants are unused. Either finish the implementation or delete the file.

## `helpers.py`

- **`count_leading_hashes` is dead code** (line 5): Defined but never imported or called anywhere in the project.

## `parse_error.py`

- **`block` is misleadingly labeled "line"** (line 7): `__str__` says `"on line {self.block}"` but `block` can be a `list[str]`. The label is wrong in both cases.
- **Not calling `super().__init__()`**: Standard Python exceptions should call `super().__init__(message)` so the message is accessible via `str(e)` and exception chaining works correctly.

## Cross-Cutting Concerns

- **No type checker configured**: `mypy` or `pyright` is absent from dev dependencies. Given the codebase uses type annotations throughout, adding one would catch many of the above issues automatically.
- **`list` shadows the built-in in multiple places**: Used as a variable name in tests and source (`test_official_app.py:28`, `test_new_recruit.py:26`, etc.).
- **`decorations` field is untested**: It is populated in `_handle_unit_line` but no test asserts on it, and it is dropped by `to_json()`.
- **Tests import private functions**: Tests directly call `_handle_faction_collection`, `_handle_unit_block`, `_handle_unit_line`, etc. The leading `_` convention signals these are not public API — either document the intent or restructure accordingly.
- **No tests for `new_recruit.py`**: The incomplete file has zero test coverage.
