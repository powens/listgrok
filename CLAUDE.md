# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

listgrok is a zero-dependency library that parses Warhammer 40k 10th edition army lists (text exported from various army-builder apps) into a common data model. Early development: APIs are unstable.

## Commands

```sh
make test        # uv run pytest --random-order
make lint        # uvx ruff check src
make format      # uvx ruff format
make typecheck   # uv run ty check src/
make coverage    # coverage run + report
make build       # uv build

uv run pytest src/tests/test_official_app.py::TestBuildTree::test_flat_single_model  # single test
uv run python examples/examples.py   # manual smoke run over examples/ (must run from repo root)
```

CI (`.github/workflows/on-main.yml`) runs lint, test, and coverage on Python 3.10–3.14. Keep the runtime dependency list empty and stick to 3.10-compatible syntax.

Tests import `listgrok` via `pythonpath = ["src"]` in `pyproject.toml`, so no install step is needed. `--random-order` is on by default — tests must not depend on execution order.

## Architecture

**Entry point.** `parse_list(text)` (`src/listgrok/parse_list.py`) tries `parse_official_app` first and falls back to `NewRecruitGWParser().parse` when it raises `ParseError`. Format detection is *by attempted parse*, not by sniffing — so a parser must raise `ParseError` (not return a half-filled `ArmyList`) when it encounters input it does not understand, or the fallback chain silently produces garbage.

**Data model** (`src/listgrok/army/army_list.py`) — plain dataclasses, shared by all parsers, each with `to_json()`:
`ArmyList` (name, points, super_faction, faction, detachment, army_size, units) → `Unit` (name, sheet_type, is_warlord, enhancement, points, composition, decorations) → `UnitComposition` (a model set: name, num_models, wargear counts).

A single-model unit still gets one `UnitComposition` named after the unit with `num_models = 1`. `decorations` is the escape hatch for body lines that are not `Nx <wargear>` and not a known keyword.

**Parsers** (`src/listgrok/parsers/`) all follow the same shape: split on blank lines into blocks, advance a small state machine (header → faction/units), and hand each block to a block handler. `helpers.py` holds shared regexes/constants (`POINTS_LABEL_REGEX`, `NUM_REGEX`, `UNIT_TYPES`, `ParserStage`, `count_leading_spaces`). `ParseError(message, block)` carries the offending block for diagnostics.

### official_app.py (GW's official 40k app)

The important detail is that the app has **multiple export dialects** and indentation — not bullet glyphs — is authoritative:

- `build_tree()` converts a unit block's body into an indentation forest of `Node`s. Bullet glyphs (`•`, `◦`) are stripped; a bulletless line inherits the indent of the most recent bulleted line, making it a *sibling* of that bullet rather than a child (dialect B writes wargear this way).
- `_populate_unit()` distinguishes multi-model from single-model units by whether any root node has children: nested children mean each root is a model set with its wargear beneath; a flat tree means one implicit model set holding all wargear.
- `_parse_faction_block()` locates the army-size line by pattern (`ARMY_SIZE_REGEX`) rather than by position, because dialects place it either last or in the middle; the remaining 2 or 3 lines map to faction/detachment (+ super_faction).
- `_handle_start()` returns `False` for exports with no army-name header (e.g. `official_3.txt`), and the caller re-reads that block as the faction block.

### new_recruit_gw.py (NewRecruit "GW" export)

Older-style parser, still class-based with string states, and driven by `count_leading_spaces` rather than a tree. It keeps its **own** `UNIT_TYPES` list (singular "CHARACTER", "DEDICATED TRANSPORT") distinct from the official-app one in `helpers.py` — do not merge them; the formats genuinely differ. Only the GW flavour is implemented; Markdown/WTC/WTC-short are not.

## Fixtures are the spec

`examples/official_app/*.txt` and `examples/nr/*.txt` are real exports and drive the tests. When adding a new export sample, add an entry to `OFFICIAL_EXAMPLES` in `src/tests/test_official_app.py` — the parametrized `TestAllOfficialExamples` checks faction metadata and unit-count for every file listed there and asserts all units are well-formed. Unit tests for `build_tree`/`parse_unit_block` state which dialect and which example file a case came from; keep that convention when adding cases.

## Agent skills

### Issue tracker

Issues live as GitHub issues in `powens/listgrok`, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles map 1:1 to labels of the same name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `CONTEXT.md` plus `docs/adr/`, both created lazily. See `docs/agents/domain.md`.
