# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

listgrok is a zero-dependency library that parses Warhammer 40k 11th edition army lists (text exported from various army-builder apps) into a common data model. Early development: APIs are unstable.

## Commands

```sh
make test        # uv run pytest
make lint        # uv run --group lint ruff check .
make format      # uv run --group lint ruff format .
make typecheck   # uv run ty check src/
make coverage    # coverage run + report
make build       # uv build

uv run pytest tests/test_official_app_units.py::TestBuildTree::test_flat_body_has_no_children  # single test
uv run python examples/examples.py   # manual smoke run over examples/
```

CI (`.github/workflows/on-main.yml`) runs lint, test, coverage, typecheck, build, and a built-wheel import smoke on Python 3.10–3.14. Keep the runtime dependency list empty and stick to 3.10-compatible syntax. Pushing a `v*` tag triggers `.github/workflows/release.yml`, which asserts the tag matches `__version__`, rebuilds, and publishes to PyPI via trusted publishing; the release steps are documented in CONTRIBUTING.md.

Tests live in `tests/` and import `listgrok` via `pythonpath = ["src"]` in `pyproject.toml`, so no install step is needed. `--random-order` is on by default (via `addopts`) — tests must not depend on execution order. The version is single-sourced from `__version__` in `src/listgrok/__init__.py` via `[tool.hatch.version]`.

## Architecture

**Entry point.** `parse_list(text)` (`src/listgrok/parse_list.py`) tries each parser in `_PARSERS` in turn — `parse_official_app`, then `parse_new_recruit_wtc` — and returns the first result that does not raise; if all raise, it raises one `ParseError` naming each parser's reason. Keep the rule that a parser raises `ParseError` (not a half-filled `ArmyList`) on input it does not understand: it is what makes a bad parse visible, and it is what makes the fallback chain work — detection is *by attempted parse*, not by sniffing, so a parser that half-accepts foreign input would shadow the ones after it.

**Data model** (`src/listgrok/models.py`) — plain dataclasses, each with `to_dict()` (stable keys: optional fields are always present, as `None`/`False`/`""`; implemented via `dataclasses.asdict`). `ParseError` lives in `src/listgrok/exceptions.py`; both are re-exported from the package root:
`ArmyList` (name, points, super_faction, faction, detachments, detachment_points, disposition, army_size, army_size_points, units) → `Unit` (name, sheet_type, is_warlord, enhancement, points, composition, decorations, attachment) → `UnitComposition` (a model set: name, num_models, wargear counts).

A single-model unit still gets one `UnitComposition` named after the unit with `num_models = 1`. `decorations` is the escape hatch for body lines that are not `Nx <wargear>` and not a known keyword. `Unit.attachment` is an `Attachment` (group, role, role_detail) for units inside an `ATTACHED UNITS` group, and `None` otherwise — attached units stay in the flat `ArmyList.units` list in file order rather than nesting under their leader.

### official_app/ (GW's official 40k app, 11th edition)

The app has two export dialects and the parser handles both: the *classic* one (`official_1/2.txt`: army-name block, indented unit bodies, ALL-CAPS headings) and the *compact* one (`official_3.txt`: no army-name block — `name` stays `""` and `points` `None` — a labelled `Force Dispositions:` line, the attached-units heading fused with its first group line, and unindented bullet-run bodies). Structured as **classify, then fold**, in four small modules:

- `blocks.py` splits the export on blank lines and classifies each block by shape alone into `ARMY_NAME`, `HEADER`, `SECTION`, `GROUP`, `UNIT` or `TRAILER`. The header block is identified by its `(N Detachment Points)` line — the one marker no other block carries. Keying off that rather than "the points line is not first" is deliberate: under the latter rule a multi-line army name has exactly the header's shape. A two-line block whose second line is a group heading is the compact dialect's fused pair and splits into `SECTION` + `GROUP`; group headings match case-insensitively (`Attached unit 1` / `Attached Unit 1`). Before the header, blocks without a `(N Points)` suffix are held and prepended to the next one: an army name can contain blank lines (`official_6/7.txt`), kept verbatim. All shared regexes live here.
- `header.py` finds the army-size, detachment and (compact dialect) `Force Dispositions:`-labelled disposition lines *by pattern, not position*, then maps the remaining 1–3 lines by order (3 → super_faction/faction/disposition, 2 → faction/disposition, 1 → faction; when the disposition was label-found, 2 → super_faction/faction). `split_detachments` splits a serial list ("A, B and C") on commas and then the final segment's last " and ", never splitting a comma-free line — so `Legends of Saga and Song` survives intact. Known limitation: a comma-free two-detachment line reads as one detachment.
- `units.py` builds the body into a forest, choosing the dialect by whether any line is indented. Classic: bullets stripped, nesting measured at the column the text starts (so an unbulleted continuation line aligned under a bulleted one is its sibling), and an `Attached as:` line never takes children (app v2.6.0 (144) out-dents it). Compact (`_run_tree`): a bulleted line followed by another bulleted line is a root; a bullet-then-plain run holds the wargear of the "Nx"-shaped root above it, or stays flat after a keyword root. Either way: if any root has children each root is a model set with its wargear beneath; a flat body collapses into one implicit model set. `Warlord`, `Enhancement(s):` and `Attached as: <role>` (parenthetical detail optional) are lifted off the roots first. Repeated wargear names sum.
- `__init__.py` folds the block stream into an `ArmyList`, carrying only the current sheet type and attachment group. It stamps the group onto each attached unit's `Attachment` (verbatim), and stamps `sheet_type` upper-cased so the compact dialect's title-case fused heading reads `ATTACHED UNITS`.

Section headings are recognised structurally (a lone ALL-CAPS line, or the line above a fused group heading), not against an allow-list, so a new GW section heading lands in `sheet_type` without a code change. `ParseError` is reserved for a malformed header block, an unparseable unit header, and an unclassifiable block.

### new_recruit_wtc/ (New Recruit's WTC export)

newrecruit.eu's "WTC" text export: a `+`-ruled header (`+ FACTION KEYWORD:`, `+ DETACHMENT:` …) then one line per unit (`[CharN: ]Nx Name (N pts)[: wargear]`) with body lines under it, ending `Created with newrecruit.eu vNN.NN`. Line-oriented, because blank lines carry no meaning here and indentation is unreliable:

- `header.py` maps `+ KEY: value` lines by key. `FACTION KEYWORD` splits on ` - ` (first → super_faction, last → faction); `DETACHMENT` drops its trailing `(rule)` and splits on commas only; U+00A0 no-break spaces in values become plain spaces. `&` lines continue an `ENHANCEMENT` and are skipped; `WARLORD`/`ENHANCEMENT`/`SECONDARY` are not stored (each unit body repeats them). Returns `NUMBER OF UNITS`, which `__init__.py` checks against the parsed count — the guard against truncated pastes.
- `units.py` classifies body lines after stripping indentation: `• Kx Model` starts a model set, `K with A, B` adds wargear × K, `Enhancement: X (+N pts)`, `Leading X[n]` and `Attached to Y[n]`; anything else is a decoration, as is a count-less numeric item like `2 Storm Bolters`. Units without bullets get one model set named after the unit.
- `__init__.py` frames the export, groups lines under unit headers, and pairs attachments: `Name[n]` is the nth unit of that name in file order. Groups are synthesised as `Attached unit N` (numbered by bodyguard file order) so they look like the official app's; `sheet_type` is always `""` because WTC has no section headings.

## Fixtures are the spec

`examples/official_app/*.txt` are real exports and drive the tests. When adding a new export sample, add an entry to `OFFICIAL_EXAMPLES` in `tests/test_official_app.py` — the parametrized `TestAllOfficialExamples` checks faction metadata and unit count for every file listed there, asserts all units are well-formed, and asserts the units' points sum to the expected total. Each entry must also carry an `attached_groups` key (the number of attached-unit groups expected), a `unit_points_total` key (the tabulated sum — the compact dialect has no list-points line to read it from), and a `decorations` key (unit name → expected decoration lines, `{}` normally; `official_3.txt`'s Wartrakk shows the compact dialect writing count-less wargear names, which land there). The tests read these keys directly — an entry missing one raises `KeyError`. Unit tests in `test_official_app_blocks.py`, `test_official_app_header.py` and `test_official_app_units.py` state which example file each case came from; keep that convention when adding cases.

`examples/new_recruit/wtc/*.txt` drive `tests/test_new_recruit_wtc.py` the same way: every file must have a `WTC_EXAMPLES` entry (a test enforces it) with `points`, `super_faction`, `faction`, `detachments`, `disposition`, `unit_count`, `attached_groups`, `warlord` and `decorations`. WTC unit points always sum to `TOTAL ARMY POINTS`, so that check reads `army_list.points` rather than a tabulated total. Reddit-sourced fixtures were de-escaped mechanically (backslash escapes and trailing hard-break spaces removed) and kept only if their indentation survived.

## Agent skills

### Issue tracker

Issues live as GitHub issues in `powens/listgrok`, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles map 1:1 to labels of the same name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `CONTEXT.md` plus `docs/adr/`, both created lazily. See `docs/agents/domain.md`.
