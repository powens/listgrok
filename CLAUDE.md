# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

listgrok is a zero-dependency library that parses Warhammer 40k 11th edition army lists (text exported from various army-builder apps) into a common data model. Early development: APIs are unstable.

## Commands

```sh
make test        # uv run pytest --random-order
make lint        # uvx ruff check src
make format      # uvx ruff format
make typecheck   # uv run ty check src/
make coverage    # coverage run + report
make build       # uv build

uv run pytest src/tests/test_official_app_units.py::TestBuildTree::test_flat_body_has_no_children  # single test
uv run python examples/examples.py   # manual smoke run over examples/ (must run from repo root)
```

CI (`.github/workflows/on-main.yml`) runs lint, test, and coverage on Python 3.10–3.14. Keep the runtime dependency list empty and stick to 3.10-compatible syntax.

Tests import `listgrok` via `pythonpath = ["src"]` in `pyproject.toml`, so no install step is needed. `--random-order` is on by default — tests must not depend on execution order.

## Architecture

**Entry point.** `parse_list(text)` (`src/listgrok/parse_list.py`) tries `parse_official_app` first and falls back to `NewRecruitGWParser().parse` when it raises `ParseError`. Format detection is *by attempted parse*, not by sniffing — so a parser must raise `ParseError` (not return a half-filled `ArmyList`) when it encounters input it does not understand, or the fallback chain silently produces garbage.

**Data model** (`src/listgrok/army/army_list.py`) — plain dataclasses, shared by all parsers, each with `to_json()`:
`ArmyList` (name, points, super_faction, faction, detachments, detachment_points, disposition, army_size, army_size_points, units) → `Unit` (name, sheet_type, is_warlord, enhancement, points, composition, decorations, attachment) → `UnitComposition` (a model set: name, num_models, wargear counts).

A single-model unit still gets one `UnitComposition` named after the unit with `num_models = 1`. `decorations` is the escape hatch for body lines that are not `Nx <wargear>` and not a known keyword. `Unit.attachment` is an `Attachment` (group, role, role_detail) for units inside an `ATTACHED UNITS` group, and `None` otherwise — attached units stay in the flat `ArmyList.units` list in file order rather than nesting under their leader.

### official_app/ (GW's official 40k app, 11th edition)

Structured as **classify, then fold**, in four small modules:

- `blocks.py` splits the export on blank lines and classifies each block by shape alone into `ARMY_NAME`, `HEADER`, `SECTION`, `GROUP`, `UNIT` or `TRAILER`. The header block is identified by its `(N Detachment Points)` line — the one marker no other block carries. Keying off that rather than "the points line is not first" is deliberate: under the latter rule a multi-line army name has exactly the header's shape. All shared regexes live here.
- `header.py` finds the army-size and detachment lines *by pattern, not position*, then maps the remaining 1–3 lines by order (3 → super_faction/faction/disposition, 2 → faction/disposition, 1 → faction). `split_detachments` splits a serial list ("A, B and C") on commas and then the final segment's last " and ", never splitting a comma-free line — so `Legends of Saga and Song` survives intact. Known limitation: a comma-free two-detachment line reads as one detachment.
- `units.py` builds the body into an indentation forest (bullets stripped, leading spaces authoritative). If any root has children each root is a model set with its wargear beneath; a flat body collapses into one implicit model set. `Warlord`, `Enhancement(s):` and `Attached as: <role> (<detail>)` are lifted off the roots first. Repeated wargear names sum.
- `__init__.py` folds the block stream into an `ArmyList`, carrying only the current sheet type and attachment group. It stamps the group onto each attached unit's `Attachment`.

Section headings are recognised structurally (a lone ALL-CAPS line), not against an allow-list, so a new GW section heading lands in `sheet_type` without a code change. `ParseError` is reserved for a malformed header block, an unparseable unit header, and an unclassifiable block.

### new_recruit_gw.py (NewRecruit "GW" export)

Older-style parser, still class-based with string states, and driven by `count_leading_spaces` rather than a tree. It keeps its own `UNIT_TYPES` list — do not merge it into the official-app patterns; the formats genuinely differ. Only the GW flavour is implemented; Markdown/WTC/WTC-short are not.

## Fixtures are the spec

`examples/official_app/*.txt` and `examples/nr/*.txt` are real exports and drive the tests. When adding a new export sample, add an entry to `OFFICIAL_EXAMPLES` in `src/tests/test_official_app.py` — the parametrized `TestAllOfficialExamples` checks faction metadata and unit count for every file listed there, asserts all units are well-formed, and asserts the units' points sum to the list total. Unit tests in `test_official_app_blocks.py`, `test_official_app_header.py` and `test_official_app_units.py` state which example file each case came from; keep that convention when adding cases.

## Agent skills

### Issue tracker

Issues live as GitHub issues in `powens/listgrok`, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles map 1:1 to labels of the same name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `CONTEXT.md` plus `docs/adr/`, both created lazily. See `docs/agents/domain.md`.
