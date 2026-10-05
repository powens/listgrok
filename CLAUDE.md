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

`parse_list(text)` (`parse_list.py`) tries each parser in `_PARSERS` in turn (`parse_official_app`: GW's official app 11th edition export plus New Recruit's export of the same layout; then `parse_new_recruit_wtc`) and returns the first result that does not raise; if all raise, one `ParseError` names each parser's reason. A parser raises `ParseError` on input it does not understand, never a half-filled `ArmyList`. That keeps a bad parse visible, and makes the fallback chain work: detection is by attempted parse, not sniffing, so a parser that half-accepts foreign input would shadow the ones after it.

**Data model** (`models.py`): dataclasses whose `to_dict()` keys are stable (optional fields present as `None`/`False`/`""`). `ArmyList` → `Unit` → `UnitComposition` (a model set: name, num_models, wargear counts). Every unit has at least one model set; a single-model unit's is named after the unit. `Unit.decorations` holds body lines that are neither `Nx <wargear>` nor a keyword, plus any footnote the app prints below the unit. `ArmyList.validation_errors` holds the app's own `ERRORS` block. Attached units stay in the flat `ArmyList.units`, in file order, with `Unit.attachment` set; other units have `attachment = None`.

### `parsers/official_app/`: classify, then fold

This is the map; module and function docstrings carry the mechanics.

- `blocks.py` classifies blank-line-separated blocks by shape alone (`ARMY_NAME`, `HEADER`, `SECTION`, `GROUP`, `UNIT`, `VALIDATION_ERRORS`, `FOOTNOTE`, `TRAILER`), keying the header off its `(N Detachment Points)` line, and splits the blocks New Recruit fuses. Home of all shared regexes.
- Localised exports: the French and German apps translate the fixed labels (detachment line, group headings, `Attached as:`, `Warlord`, `Enhancement(s):`, army sizes, joiners, footer) and use locale thousands separators (`2.000`, `2'000`, no-break spaces). Each pattern accepts those forms. Attached-as roles and details are normalised to English (`ROLE_NAMES`/`ROLE_DETAILS` in `units.py`); every other string stays verbatim.
- `header.py` reads faction metadata: labelled lines by pattern, the 1–3 left over by order. `split_detachments` keeps names in `COMPOUND_DETACHMENTS` (`detachment_names.py`) whole; that set is regenerated from GW's app data (English, French and German names) by the maintainer-local `refresh-detachment-names` skill and only ever grows.
- `units.py` builds a unit body into a forest in one of three dialects: *classic* (indented), *compact* (unindented bullet runs, `_run_tree`) or *glyph* (unindented, every line bulleted, `_glyph_tree`). `Warlord`, `Enhancement(s):` and `Attached as:` are lifted off the roots and off a model set's children.
- `__init__.py` reads the army name and points from the text before the header, then folds the blocks into an `ArmyList`, carrying only the current sheet type and attachment group.

Section headings are recognised structurally, not from an allow-list, so a new GW heading lands in `sheet_type` with no code change. `ParseError` is reserved for a missing or malformed header, an unparseable unit header, an unclassifiable block after the header, and a footnote not directly below a `*`-marked unit.

### new_recruit_wtc/ (New Recruit's WTC export)

newrecruit.eu's "WTC" text export: a `+`-ruled header (`+ FACTION KEYWORD:`, `+ DETACHMENT:` …) then one line per unit (`[CharN: ]Nx Name (N pts)[: wargear]`) with body lines under it, ending `Created with newrecruit.eu vNN.NN`. Line-oriented, because blank lines carry no meaning here and indentation is unreliable:

- `header.py` maps `+ KEY: value` lines by key. `FACTION KEYWORD` splits on ` - ` (first → super_faction, last → faction); `DETACHMENT` drops its trailing `(rule)` and splits on commas only; U+00A0 no-break spaces in values become plain spaces. `&` lines continue an `ENHANCEMENT` and are skipped; `WARLORD`/`ENHANCEMENT`/`SECONDARY` are not stored (each unit body repeats them). Returns `NUMBER OF UNITS`, which `__init__.py` checks against the parsed count — the guard against truncated pastes.
- `units.py` classifies body lines after stripping indentation: `• Kx Model` starts a model set, `K with A, B` adds wargear × K, `Enhancement: X (+N pts)`, `Leading X[n]` and `Attached to Y[n]`; anything else is a decoration, as is a count-less numeric item like `2 Storm Bolters`. Units without bullets get one model set named after the unit.
- `__init__.py` frames the export, groups lines under unit headers, and pairs attachments: `Name[n]` is the nth unit of that name in file order. Groups are synthesised as `Attached unit N` (numbered by bodyguard file order) so they look like the official app's; `sheet_type` is always `""` because WTC has no section headings.

## Fixtures are the spec

`examples/official_app/` holds real exports: `official_*.txt`, `lvo2026_*.txt` (LVO 2026 lists via listhammer; unindented app v2.6.0 exports, some hand-annotated), and `listhammer_*.txt` (Sept–Nov 2026 lists via listhammer.info's `/api/recentLists`, picked for forms the others lack: French/German, locale separators, `ERRORS`, footnotes; player names redacted). Every file there except `lvo2026_genestealer_cults.txt`, which does not parse, is an `OFFICIAL_EXAMPLES` entry in `tests/test_official_app.py`, checked end to end by `TestAllOfficialExamples`.

To add an export, add an `OFFICIAL_EXAMPLES` entry (an `nr_`-prefixed key reads from `examples/new_recruit/official/`). Every entry needs `attached_groups`, `unit_points_total` and `decorations` keys; the comments in `test_units_are_well_formed` explain the `decorations` value forms. Cases in `test_official_app_{blocks,header,units}.py` name the example file they came from; keep that convention.

`examples/new_recruit/wtc/*.txt` drive `tests/test_new_recruit_wtc.py` the same way: every file must have a `WTC_EXAMPLES` entry (a test enforces it) with `points`, `super_faction`, `faction`, `detachments`, `disposition`, `unit_count`, `attached_groups`, `warlord` and `decorations`. WTC unit points always sum to `TOTAL ARMY POINTS`, so that check reads `army_list.points` rather than a tabulated total. Reddit-sourced fixtures were de-escaped mechanically (backslash escapes and trailing hard-break spaces removed) and kept only if their indentation survived.

In no test, because no parser handles their format yet: `nr_official_0–1.txt` and `nr_other_0.txt` under `examples/new_recruit/`, `examples/ironbuilt/`, and `examples/unknown/`. `official_1`–`official_10` were deleted (cases citing them: git `6bc7874`); the compact and glyph code they covered stays, because the `lvo2026_*` exports need it.

## Agent skills

- Issues: GitHub issues in `powens/listgrok` via `gh` — `docs/agents/issue-tracker.md`.
- Triage: the five canonical roles map 1:1 to same-named labels — `docs/agents/triage-labels.md`.
- Domain docs: root `CONTEXT.md` plus `docs/adr/`, created lazily — `docs/agents/domain.md`.
