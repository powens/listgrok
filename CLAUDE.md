# CLAUDE.md

listgrok is a zero-dependency library that parses Warhammer 40k 11th edition army lists (text exported from army-builder apps) into a common data model. Early development: APIs are unstable.

## Commands

```sh
make test | lint | format | typecheck | coverage | coverage-html | build   # see Makefile
uv run pytest tests/test_official_app_units.py::TestBuildTree::test_flat_body_has_no_children  # one test
uv run python examples/examples.py   # smoke run over examples/official_app/
```

- The runtime dependency list stays empty, and syntax stays 3.10-compatible (CI runs 3.10–3.15).
- Tests import `listgrok` from `src/` via pytest's `pythonpath`, so no install step. `--random-order` is always on: tests must be order-independent.
- The version lives only in `__version__` (`src/listgrok/__init__.py`). A `v*` tag publishes to PyPI; release steps are in CONTRIBUTING.md.

## Architecture

`parse_list(text)` delegates to `parse_official_app`, the only parser: GW's official app 11th edition export, plus New Recruit's export of the same layout. A parser raises `ParseError` on input it does not understand, never a half-filled `ArmyList`. That keeps a bad parse visible, and lets a future second format be detected by attempted parse rather than by sniffing.

**Data model** (`models.py`): dataclasses whose `to_dict()` keys are stable (optional fields present as `None`/`False`/`""`). `ArmyList` → `Unit` → `UnitComposition` (a model set: name, num_models, wargear counts). Every unit has at least one model set; a single-model unit's is named after the unit. `Unit.decorations` holds body lines that are neither `Nx <wargear>` nor a keyword. Attached units stay in the flat `ArmyList.units`, in file order, with `Unit.attachment` set; other units have `attachment = None`.

### `parsers/official_app/`: classify, then fold

This is the map; module and function docstrings carry the mechanics.

- `blocks.py` classifies blank-line-separated blocks by shape alone (`ARMY_NAME`, `HEADER`, `SECTION`, `GROUP`, `UNIT`, `TRAILER`), keying the header off its `(N Detachment Points)` line, and splits the blocks New Recruit fuses. Home of all shared regexes.
- `header.py` reads faction metadata: labelled lines by pattern, the 1–3 left over by order. `split_detachments` keeps names in `COMPOUND_DETACHMENTS` (`detachment_names.py`) whole; that set is regenerated from GW's app data by the maintainer-local `refresh-detachment-names` skill and only ever grows.
- `units.py` builds a unit body into a forest in one of three dialects: *classic* (indented), *compact* (unindented bullet runs, `_run_tree`) or *glyph* (unindented, every line bulleted, `_glyph_tree`). `Warlord`, `Enhancement(s):` and `Attached as:` are lifted off the roots and off a model set's children.
- `__init__.py` reads the army name and points from the text before the header, then folds the blocks into an `ArmyList`, carrying only the current sheet type and attachment group.

Section headings are recognised structurally, not from an allow-list, so a new GW heading lands in `sheet_type` with no code change. `ParseError` is reserved for a missing or malformed header, an unparseable unit header, and an unclassifiable block after the header.

## Fixtures are the spec

`examples/official_app/` holds real exports: `official_*.txt`, and `lvo2026_*.txt` (LVO 2026 lists via listhammer; unindented app v2.6.0 exports, some hand-annotated). Every file there except `lvo2026_genestealer_cults.txt`, which does not parse, is an `OFFICIAL_EXAMPLES` entry in `tests/test_official_app.py`, checked end to end by `TestAllOfficialExamples`.

To add an export, add an `OFFICIAL_EXAMPLES` entry (an `nr_`-prefixed key reads from `examples/new_recruit/official/`). Every entry needs `attached_groups`, `unit_points_total` and `decorations` keys; the comments in `test_units_are_well_formed` explain the `decorations` value forms. Cases in `test_official_app_{blocks,header,units}.py` name the example file they came from; keep that convention.

In no test, because no parser handles their format yet: `nr_official_0–1.txt` and `nr_other_0.txt` under `examples/new_recruit/`, `examples/ironbuilt/`, and `examples/unknown/`. `official_1`–`official_10` were deleted (cases citing them: git `6bc7874`); the compact and glyph code they covered stays, because the `lvo2026_*` exports need it.

## Agent skills

- Issues: GitHub issues in `powens/listgrok` via `gh` — `docs/agents/issue-tracker.md`.
- Triage: the five canonical roles map 1:1 to same-named labels — `docs/agents/triage-labels.md`.
- Domain docs: root `CONTEXT.md` plus `docs/adr/`, created lazily — `docs/agents/domain.md`.
