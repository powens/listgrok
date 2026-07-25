# Official App 11th Edition Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace listgrok's 10th edition GW official-app parser with a greenfield parser for the 11th edition export format, which adds attached units, a disposition line, detachment points, multiple detachments, and comma-formatted point totals.

**Architecture:** Classify-then-fold. `blocks.py` splits the export on blank lines and classifies each block by shape into a typed stream (`ARMY_NAME`, `HEADER`, `SECTION`, `GROUP`, `UNIT`, `TRAILER`); `header.py` and `units.py` turn individual blocks into data; `__init__.py` folds the stream into an `ArmyList` carrying only two variables (current sheet type, current attachment group). No lookahead, no backtracking, no state machine.

**Tech Stack:** Python 3.10+, standard library only. pytest (`--random-order`), ruff, ty, uv.

## Global Constraints

- **Zero runtime dependencies.** `pyproject.toml`'s `dependencies = []` must stay empty. Standard library only in `src/listgrok/`.
- **Python 3.10-compatible syntax.** CI runs 3.10 through 3.14. `X | None` in annotations is fine (PEP 604 landed in 3.10); `match` statements are fine; anything 3.11+ only is not.
- **Tests must not depend on execution order.** `--random-order` is on by default via `make test`.
- **Import path for tests** is `pythonpath = ["src"]` in `pyproject.toml` — no install step, import as `from listgrok...`.
- **A parser raises `ParseError` rather than returning a half-filled `ArmyList`.** `parse_list` falls back on `ParseError`, so a partial return silently produces garbage.
- **Commit message style:** plain imperative subject lines matching repo history (`Add official_app_v2 parser and share parser constants`). Not conventional-commits. **Do not add `Co-Authored-By` trailers.**
- **Fixtures are the spec.** `examples/official_app/*.txt` are real exports; expected values come from reading them, never from adjusting a fixture to match the code.
- Verification commands: `make test`, `make lint`, `make typecheck`.

## Reference: the 11th edition format

Both fixtures were exported by `App Version: v2.3.0 (1), Data Version: v912`.

```
Awoo (1,260 Points)                                     <- army name + points

Space Marines                                           <- super-faction
Space Wolves                                            <- faction
Champions of Fenris, Legends of Saga and Song and Veterans of the Fang (3 Detachment Points)
Disruption                                              <- disposition
Strike Force (2,000 Points)                             <- army size + cap

ATTACHED UNITS                                          <- section heading

Attached unit 1                                         <- attachment-group heading

Ragnar Blackmane (90 Points)
  • Attached as: Leader (Character)
  • 1x Bolt Pistol

Blood Claws (135 Points)
  • Attached as: Bodyguard (Battleline)
  • 1x Blood Claw Pack Leader
     ◦ 1x Astartes chainsword
  • 9x Blood Claw
     ◦ 9x Astartes chainsword

CHARACTERS

Logan Grimnar (100 Points)
  • Warlord
  • 1x Axe Morkai

Exported with App Version: v2.3.0 (1), Data Version: v912   <- trailer
```

Bullets are `•` (U+2022) at indent 2 and `◦` (U+25E6) at indent 5. Apostrophes in
faction and model names are the typographic `’` (U+2019), not `'` — copy them
exactly.

## File Structure

| File | Responsibility |
|---|---|
| `src/listgrok/army/army_list.py` | **Modify.** Add `Attachment`; add `attachment` to `Unit`; replace `detachment` with `detachments`, add `detachment_points`, `disposition`, `army_size_points` on `ArmyList`. |
| `src/listgrok/parsers/official_app/__init__.py` | **Create.** `parse_official_app` — folds the block stream into an `ArmyList`. |
| `src/listgrok/parsers/official_app/blocks.py` | **Create.** Regexes, `BlockKind`, `Block`, `classify_blocks`. Knows text shapes, not army lists. |
| `src/listgrok/parsers/official_app/header.py` | **Create.** `parse_header`, `split_detachments`. |
| `src/listgrok/parsers/official_app/units.py` | **Create.** `Node`, `build_tree`, `parse_unit`. |
| `src/listgrok/parsers/official_app.py` | **Delete.** Superseded by the package — a module and a package of the same name cannot coexist. |
| `src/listgrok/parsers/helpers.py` | **Modify.** Strip constants that only 10th ed used; keep `count_leading_spaces`. |
| `src/listgrok/parsers/new_recruit_gw.py` | **Modify.** It writes `ArmyList.detachment` via `setattr`; follow the field rename to `detachments`. |
| `src/tests/test_new_recruit.py` | **Modify.** Six assertions read `army_list.detachment`. |
| `src/listgrok/parse_list.py` | **Modify.** Point at the new parser. |
| `src/tests/test_official_app.py` | **Delete then recreate.** Old version tests deleted fixtures; new version is end-to-end. |
| `src/tests/test_official_app_blocks.py` | **Create.** Classification. |
| `src/tests/test_official_app_header.py` | **Create.** Metadata block and detachment splitting. |
| `src/tests/test_official_app_units.py` | **Create.** Unit blocks and indent trees. |
| `src/tests/test_parse_list.py` | **Create.** Dispatch and fallback. |
| `examples/official_app/official_1.txt`, `official_2.txt` | **Commit.** Currently untracked. |
| `CLAUDE.md`, `pyproject.toml` | **Modify.** Docs describe 10th ed. |

---

### Task 1: Remove 10th edition support and commit the 11th edition fixtures

The repo is currently red: commit `4c1b7bc` deleted the eight 10th ed example
files that `src/tests/test_official_app.py` reads, so `make test` reports 18
failures. This task ends with a green suite and no 10th ed code.

**Files:**
- Delete: `src/listgrok/parsers/official_app.py`
- Delete: `src/tests/test_official_app.py`
- Modify: `src/listgrok/parsers/helpers.py`
- Modify: `src/listgrok/parse_list.py`
- Add to git: `examples/official_app/official_1.txt`, `examples/official_app/official_2.txt`

**Interfaces:**
- Consumes: nothing.
- Produces: a repo where `listgrok.parsers.helpers` exports only `count_leading_spaces(line: str) -> int`, and `listgrok.parsers.official_app` does not exist.

- [ ] **Step 1: Confirm the starting state**

Run: `uv run pytest -q 2>&1 | tail -3`
Expected: `18 failed, 31 passed`. The 18 failures are all in `test_official_app.py`.

- [ ] **Step 2: Delete the 10th edition parser and its tests**

```bash
git rm src/listgrok/parsers/official_app.py src/tests/test_official_app.py
```

- [ ] **Step 3: Strip the 10th-edition-only helpers**

Replace the entire contents of `src/listgrok/parsers/helpers.py` with:

```python
def count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip())
```

`POINTS_LABEL_REGEX`, `NUM_REGEX`, `UNIT_TYPES`, `ParserStage` and
`count_leading_hashes` all had exactly one consumer — the deleted parser — or
none at all. `count_leading_spaces` stays because `new_recruit_gw.py` uses it.

- [ ] **Step 4: Point `parse_list` at NewRecruit only, temporarily**

Replace the entire contents of `src/listgrok/parse_list.py` with:

```python
from listgrok.army.army_list import ArmyList
from listgrok.parsers.new_recruit_gw import NewRecruitGWParser


def parse_list(list_text: str) -> ArmyList:
    return NewRecruitGWParser().parse(list_text)
```

This is deliberately temporary; Task 6 restores the official-app path. Until
then `examples/examples.py`'s `official_app()` function will not work — that is
a manual smoke script, not a test, so nothing in CI notices.

- [ ] **Step 5: Verify the suite is green**

Run: `make test`
Expected: `31 passed`, 0 failed. Only `test_helpers.py` and
`test_new_recruit.py` remain.

- [ ] **Step 6: Verify lint and types**

Run: `make lint && make typecheck`
Expected: both clean. If ruff reports an unused import in `parse_list.py`, the
file content in Step 4 was not copied exactly — recopy it.

- [ ] **Step 7: Commit, including the two 11th edition fixtures**

```bash
git add examples/official_app/official_1.txt examples/official_app/official_2.txt
git add src/listgrok/parsers/helpers.py src/listgrok/parse_list.py
git commit -m "Remove 10th edition official app parser

Its example fixtures were deleted in 4c1b7bc, leaving the suite red. 11th
edition support is a greenfield replacement, so the 10th ed parser, its tests
and the helpers only it used all go. parse_list falls back to NewRecruit alone
until the new parser lands.

Adds the two 11th edition exports that drive the new parser."
```

---

### Task 2: Extend the data model

**Files:**
- Modify: `src/listgrok/army/army_list.py`
- Modify: `src/listgrok/parsers/new_recruit_gw.py:21-34`
- Modify: `src/tests/test_new_recruit.py` (6 assertions)
- Test: `src/tests/test_army_list.py` (create)

**Watch out:** `new_recruit_gw._handle_header` writes the field with
`setattr(army_list, "detachment", ...)`. `ArmyList` is a plain dataclass with no
`__slots__`, so after the rename that `setattr` **will not raise** — it silently
creates a stray instance attribute, `to_json()` drops it, and
`test_new_recruit.py`'s `army_list.detachment` assertions keep passing while
reading that stray attribute. Nothing fails; the data just goes missing. Step 5
below is what catches it, so do not skip it.

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Attachment(group: str = "", role: str = "", role_detail: str = "")` with `to_json() -> dict`
  - `Unit(..., attachment: Attachment | None = None)`
  - `ArmyList(name, points, super_faction, faction, detachments: list[str], detachment_points: int | None, disposition: str, army_size: str, army_size_points: int | None, units)`
  - `UnitComposition.add_wargear(weapon: str, count: int)` (unchanged) — sums repeated names
  - `ArmyList.add_unit(unit)`, `Unit.add_model_set(model_set)` (unchanged)

- [ ] **Step 1: Write the failing tests**

Create `src/tests/test_army_list.py`:

```python
from listgrok.army.army_list import ArmyList, Attachment, Unit, UnitComposition


def test_repeated_wargear_sums():
    model_set = UnitComposition(name="Commander", num_models=1)
    model_set.add_wargear("Missile pod", 1)
    model_set.add_wargear("Missile pod", 3)

    assert model_set.wargear == {"Missile pod": 4}


def test_unit_json_omits_attachment_when_absent():
    unit = Unit(name="Ghostkeel Battlesuit", points=150)

    assert "attachment" not in unit.to_json()
    assert "is_warlord" not in unit.to_json()


def test_unit_json_includes_attachment_when_present():
    unit = Unit(
        name="Ragnar Blackmane",
        points=90,
        is_warlord=True,
        attachment=Attachment(
            group="Attached unit 1", role="Leader", role_detail="Character"
        ),
    )

    o = unit.to_json()
    assert o["is_warlord"] is True
    assert o["attachment"] == {
        "group": "Attached unit 1",
        "role": "Leader",
        "role_detail": "Character",
    }


def test_army_list_json_carries_the_11th_edition_fields():
    army_list = ArmyList(
        name="Awoo",
        points=1260,
        super_faction="Space Marines",
        faction="Space Wolves",
        detachments=["Champions of Fenris", "Veterans of the Fang"],
        detachment_points=3,
        disposition="Disruption",
        army_size="Strike Force",
        army_size_points=2000,
    )

    o = army_list.to_json()
    assert o["detachments"] == ["Champions of Fenris", "Veterans of the Fang"]
    assert o["detachment_points"] == 3
    assert o["disposition"] == "Disruption"
    assert o["army_size"] == "Strike Force"
    assert o["army_size_points"] == 2000
    assert o["super_faction"] == "Space Marines"


def test_army_list_json_omits_super_faction_when_absent():
    assert "super_faction" not in ArmyList(faction="T’au Empire").to_json()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest src/tests/test_army_list.py -v`
Expected: FAIL — `ImportError: cannot import name 'Attachment'`.

- [ ] **Step 3: Write the implementation**

Replace the entire contents of `src/listgrok/army/army_list.py` with:

```python
from dataclasses import dataclass, field


@dataclass
class Attachment:
    """How a unit joins an attached unit — GW's 11th edition leader/bodyguard pairing."""

    group: str = ""  # "Attached unit 1" — the group heading, verbatim
    role: str = ""  # "Leader" | "Bodyguard"
    role_detail: str = ""  # "Character" | "Battleline" | "" — the parenthetical

    def to_json(self) -> dict:
        return {
            "group": self.group,
            "role": self.role,
            "role_detail": self.role_detail,
        }


@dataclass
class UnitComposition:
    name: str = ""
    num_models: int | None = None
    wargear: dict[str, int] = field(default_factory=dict)

    def add_wargear(self, weapon: str, count: int):
        if weapon not in self.wargear:
            self.wargear[weapon] = count
        else:
            self.wargear[weapon] += count

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "num_models": self.num_models,
            "wargear": self.wargear,
        }


@dataclass
class Unit:
    name: str = ""
    sheet_type: str = ""
    is_warlord: bool = False
    enhancement: str = ""
    points: int | None = None
    composition: list[UnitComposition] = field(default_factory=list)
    decorations: list[str] = field(default_factory=list)
    attachment: Attachment | None = None

    def add_model_set(self, model_set: UnitComposition):
        self.composition.append(model_set)

    def to_json(self) -> dict:
        o: dict = {
            "name": self.name,
            "sheet_type": self.sheet_type,
            "enhancement": self.enhancement,
            "points": self.points,
            "composition": [model.to_json() for model in self.composition],
            "decorations": self.decorations,
        }
        if self.is_warlord:
            o["is_warlord"] = self.is_warlord
        if self.attachment is not None:
            o["attachment"] = self.attachment.to_json()
        return o


@dataclass
class ArmyList:
    name: str = ""
    points: int | None = None
    super_faction: str = ""
    faction: str = ""
    detachments: list[str] = field(default_factory=list)
    detachment_points: int | None = None
    disposition: str = ""
    army_size: str = ""
    army_size_points: int | None = None
    units: list[Unit] = field(default_factory=list)

    def add_unit(self, unit: Unit):
        self.units.append(unit)

    def to_json(self) -> dict:
        o: dict = {
            "name": self.name,
            "points": self.points,
            "faction": self.faction,
            "detachments": self.detachments,
            "detachment_points": self.detachment_points,
            "disposition": self.disposition,
            "army_size": self.army_size,
            "army_size_points": self.army_size_points,
            "units": [unit.to_json() for unit in self.units],
        }
        if self.super_faction:
            o["super_faction"] = self.super_faction

        return o
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest src/tests/test_army_list.py -v`
Expected: 5 passed.

- [ ] **Step 5: Follow the rename through the NewRecruit parser**

In `src/listgrok/parsers/new_recruit_gw.py`, replace `_handle_header` (lines
21-34) with:

```python
def _handle_header(lines: list[str], army_list: ArmyList):
    header = "\n".join(lines)
    matches = [
        # ("list_name", "")
        ("points", POINTS_REGEX, int),
        ("faction", FACTION_REGEX, str),
    ]

    for key, regex, type in matches:
        match = re.search(regex, header, flags=re.MULTILINE)
        if match is not None:
            val = type(match.group(key))
            setattr(army_list, key, val)

    # Handled separately from the setattr loop: the export names one
    # detachment, the model holds a list of them.
    detachment = re.search(DETACHMENT_REGEX, header, flags=re.MULTILINE)
    if detachment is not None:
        army_list.detachments = [detachment.group("detachment")]
```

- [ ] **Step 6: Update the NewRecruit assertions**

In `src/tests/test_new_recruit.py`, there are six assertions reading
`army_list.detachment`. Find them with:

Run: `grep -n "\.detachment" src/tests/test_new_recruit.py`

Rewrite each one as a list:

```python
# was: assert army_list.detachment == "Experimental Prototype Cadre"
assert army_list.detachments == ["Experimental Prototype Cadre"]

# was: assert army_list.detachment == ""      (the missing-detachment case)
assert army_list.detachments == []
```

- [ ] **Step 7: Prove no stray `detachment` attribute survives**

Run: `grep -rn --include='*.py' "\.detachment\b" src/`
Expected: **no output.** Every remaining reference must be `detachments`. A hit
here is the silent-divergence bug described above.

- [ ] **Step 8: Check nothing else broke**

Run: `make test && make lint && make typecheck`
Expected: all green, including `test_new_recruit.py`.

- [ ] **Step 9: Commit**

```bash
git add src/listgrok/army/army_list.py src/tests/test_army_list.py \
        src/listgrok/parsers/new_recruit_gw.py src/tests/test_new_recruit.py
git commit -m "Extend the data model for 11th edition army lists

Adds Attachment (group, role, role_detail) and hangs it off Unit, so an
attached unit's leader/bodyguard pairing is visible while units stay in one
flat list in file order.

On ArmyList: detachment becomes detachments (a list, since 11th allows
several), plus detachment_points, disposition, and army_size_points so the
points cap is comparable against the list total without re-parsing a string.

The NewRecruit parser follows the rename: it wrote the field via setattr, which
would have kept working silently against a stray instance attribute."
```

---

### Task 3: Block classification (`blocks.py`)

**Files:**
- Create: `src/listgrok/parsers/official_app/__init__.py` (empty for now)
- Create: `src/listgrok/parsers/official_app/blocks.py`
- Test: `src/tests/test_official_app_blocks.py`

**Interfaces:**
- Consumes: `ParseError(message: str, block: str | list[str])` from `listgrok.parsers.parse_error`.
- Produces, all importable from `listgrok.parsers.official_app.blocks`:
  - `BlockKind` — enum with members `ARMY_NAME`, `HEADER`, `SECTION`, `GROUP`, `UNIT`, `TRAILER`
  - `Block` — frozen dataclass with `kind: BlockKind` and `lines: list[str]`
  - `classify_blocks(text: str) -> list[Block]`
  - `parse_points(text: str) -> int` — strips thousands commas
  - Compiled patterns `POINTS_REGEX`, `DETACHMENT_REGEX`, `NUM_REGEX`, `ATTACHED_AS_REGEX`, `BULLET_REGEX`

- [ ] **Step 1: Write the failing tests**

Create `src/tests/test_official_app_blocks.py`:

```python
import pytest

from listgrok.parsers.official_app.blocks import (
    BlockKind,
    classify_blocks,
    parse_points,
)
from listgrok.parsers.parse_error import ParseError

# Trimmed from official_1.txt: one of each block kind.
MINIMAL = """11th stuff (2,000 Points)

T’au Empire
Retaliation Cadre (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

CHARACTERS

Commander Farsight (70 Points)
  • 1x Dawn Blade

Exported with App Version: v2.3.0 (1), Data Version: v912
"""

# Trimmed from official_1.txt: the attached-units section.
ATTACHED = """11th stuff (2,000 Points)

T’au Empire
Retaliation Cadre (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

ATTACHED UNITS

Attached unit 1

Commander Farsight (70 Points)
  • Attached as: Leader (Character)
  • 1x Dawn Blade
"""

NO_ARMY_NAME = """T’au Empire
Retaliation Cadre (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

CHARACTERS

Commander Farsight (70 Points)
  • 1x Dawn Blade
"""


def test_classifies_one_of_each_block_kind():
    assert [block.kind for block in classify_blocks(MINIMAL)] == [
        BlockKind.ARMY_NAME,
        BlockKind.HEADER,
        BlockKind.SECTION,
        BlockKind.UNIT,
        BlockKind.TRAILER,
    ]


def test_group_heading_is_not_a_section_heading():
    # "ATTACHED UNITS" is all caps and is a section; "Attached unit 1" is not.
    assert [block.kind for block in classify_blocks(ATTACHED)] == [
        BlockKind.ARMY_NAME,
        BlockKind.HEADER,
        BlockKind.SECTION,
        BlockKind.GROUP,
        BlockKind.UNIT,
    ]


def test_header_keeps_its_lines_verbatim():
    header = classify_blocks(MINIMAL)[1]

    assert header.lines == [
        "T’au Empire",
        "Retaliation Cadre (3 Detachment Points)",
        "Purge the Foe",
        "Strike Force (2,000 Points)",
    ]


def test_unit_block_keeps_its_indented_body():
    unit = classify_blocks(MINIMAL)[3]

    assert unit.lines == ["Commander Farsight (70 Points)", "  • 1x Dawn Blade"]


def test_list_with_no_army_name_starts_at_the_header():
    assert [block.kind for block in classify_blocks(NO_ARMY_NAME)] == [
        BlockKind.HEADER,
        BlockKind.SECTION,
        BlockKind.UNIT,
    ]


def test_multi_line_army_name_stays_one_block():
    text = "Line one of the name\nand line two (2,000 Points)\n\n" + NO_ARMY_NAME
    blocks = classify_blocks(text)

    assert blocks[0].kind == BlockKind.ARMY_NAME
    assert blocks[0].lines == ["Line one of the name", "and line two (2,000 Points)"]


def test_text_with_no_header_raises():
    # A NewRecruit export: no "(N Detachment Points)" line anywhere.
    with pytest.raises(ParseError):
        classify_blocks("+ FACTION KEYWORD: Xenos - T’au Empire\n")


def test_unclassifiable_block_after_the_header_raises():
    with pytest.raises(ParseError):
        classify_blocks(NO_ARMY_NAME + "\nstray line one\nstray line two\n")


def test_unclassifiable_block_before_the_header_raises():
    with pytest.raises(ParseError):
        classify_blocks("stray line\n\n" + NO_ARMY_NAME)


@pytest.mark.parametrize("text,expected", [("2,000", 2000), ("70", 70), ("1,260", 1260)])
def test_parse_points_strips_thousands_commas(text, expected):
    assert parse_points(text) == expected
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest src/tests/test_official_app_blocks.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'listgrok.parsers.official_app'`.

- [ ] **Step 3: Create the package and write the classifier**

Create `src/listgrok/parsers/official_app/__init__.py` as an empty file (Task 6
fills it in).

Create `src/listgrok/parsers/official_app/blocks.py`:

```python
"""Split a GW official-app (11th edition) export into classified blocks.

Classification is by shape alone — no army-list knowledge lives here. The
metadata block is identified by its "(N Detachment Points)" line, which no other
block carries; everything before it is the army name, everything after it is
section headings, attachment-group headings and unit blocks. Keying off that
line rather than off "the points line is not first" is what lets a multi-line
army name work: under the latter rule it has exactly the header's shape.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto

from listgrok.parsers.parse_error import ParseError

# re.DOTALL so a multi-line army name matches as a single name. Point totals may
# carry thousands commas ("2,000 Points").
POINTS_REGEX = re.compile(
    r"^(?P<name>.+?)\s\((?P<points>[\d,]+)\s[Pp]oints\)$", re.DOTALL
)
DETACHMENT_REGEX = re.compile(
    r"^(?P<name>.+?)\s\((?P<points>\d+)\sDetachment\s[Pp]oints?\)$"
)
NUM_REGEX = re.compile(r"^(?P<num>\d+)x\s(?P<name>.+)$")
ATTACHED_AS_REGEX = re.compile(
    r"^Attached as:\s*(?P<role>[^(]+?)\s*\((?P<detail>[^)]*)\)$"
)
BULLET_REGEX = re.compile(r"^[•◦]\s*")
TRAILER_PREFIX = "Exported with App Version:"


class BlockKind(Enum):
    ARMY_NAME = auto()
    HEADER = auto()
    SECTION = auto()
    GROUP = auto()
    UNIT = auto()
    TRAILER = auto()


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    lines: list[str]


def parse_points(text: str) -> int:
    return int(text.replace(",", ""))


def split_blocks(text: str) -> list[list[str]]:
    """Group non-blank lines into blocks, dropping the blank separators."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.split("\n"):
        if line.strip():
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def classify_blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    seen_header = False
    for lines in split_blocks(text):
        kind = _classify(lines, seen_header)
        seen_header = seen_header or kind is BlockKind.HEADER
        blocks.append(Block(kind=kind, lines=lines))

    if not seen_header:
        raise ParseError("No header block found", text)
    return blocks


def _classify(lines: list[str], seen_header: bool) -> BlockKind:
    if lines[0].startswith(TRAILER_PREFIX):
        return BlockKind.TRAILER

    if any(DETACHMENT_REGEX.match(line.strip()) for line in lines):
        return BlockKind.HEADER

    if not seen_header:
        if POINTS_REGEX.match("\n".join(lines).strip()):
            return BlockKind.ARMY_NAME
        raise ParseError("Unrecognised block before the header", lines)

    if POINTS_REGEX.match(lines[0].strip()):
        return BlockKind.UNIT

    if len(lines) == 1:
        line = lines[0].strip()
        return BlockKind.SECTION if _is_section_heading(line) else BlockKind.GROUP

    raise ParseError("Unrecognised block", lines)


def _is_section_heading(line: str) -> bool:
    """A section heading shouts: "ATTACHED UNITS", not "Attached unit 1"."""
    return any(char.isalpha() for char in line) and line == line.upper()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest src/tests/test_official_app_blocks.py -q`
Expected: 12 passed.

- [ ] **Step 5: Verify the fixtures classify without raising**

Run:

```bash
PYTHONPATH=src uv run python -c "
from pathlib import Path
from listgrok.parsers.official_app.blocks import classify_blocks
for name in ('official_1.txt', 'official_2.txt'):
    text = (Path('examples/official_app') / name).read_text()
    kinds = [b.kind.name for b in classify_blocks(text)]
    print(name, len(kinds), sorted(set(kinds)))
"
```

Expected exactly (block counts verified by hand against the fixtures):

```
official_1.txt 28 ['ARMY_NAME', 'GROUP', 'HEADER', 'SECTION', 'TRAILER', 'UNIT']
official_2.txt 16 ['ARMY_NAME', 'GROUP', 'HEADER', 'SECTION', 'TRAILER', 'UNIT']
```

A lower count means blocks are being merged; a `ParseError` means a real block
shape is unaccounted for.

- [ ] **Step 6: Lint and typecheck**

Run: `make lint && make typecheck`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add src/listgrok/parsers/official_app/ src/tests/test_official_app_blocks.py
git commit -m "Add 11th edition block classification

First pass of the parser: split the export on blank lines and classify each
block by shape into a typed stream. The metadata block is found by its
'(N Detachment Points)' line, the one marker no other block carries, so army
name, sections, attachment groups and units all fall out without lookahead."
```

---

### Task 4: The metadata block (`header.py`)

**Files:**
- Create: `src/listgrok/parsers/official_app/header.py`
- Test: `src/tests/test_official_app_header.py`

**Interfaces:**
- Consumes: `POINTS_REGEX`, `DETACHMENT_REGEX`, `parse_points` from `blocks.py`; `ArmyList` from `listgrok.army.army_list`; `ParseError`.
- Produces:
  - `parse_header(lines: list[str], army_list: ArmyList) -> None` — mutates the `ArmyList` in place
  - `split_detachments(text: str) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `src/tests/test_official_app_header.py`:

```python
import pytest

from listgrok.army.army_list import ArmyList
from listgrok.parsers.official_app.header import parse_header, split_detachments
from listgrok.parsers.parse_error import ParseError


def test_official_1_header_has_no_super_faction():
    army_list = ArmyList()
    parse_header(
        [
            "T’au Empire",
            "Retaliation Cadre (3 Detachment Points)",
            "Purge the Foe",
            "Strike Force (2,000 Points)",
        ],
        army_list,
    )

    assert army_list.super_faction == ""
    assert army_list.faction == "T’au Empire"
    assert army_list.detachments == ["Retaliation Cadre"]
    assert army_list.detachment_points == 3
    assert army_list.disposition == "Purge the Foe"
    assert army_list.army_size == "Strike Force"
    assert army_list.army_size_points == 2000


def test_official_2_header_has_a_super_faction_and_three_detachments():
    army_list = ArmyList()
    parse_header(
        [
            "Space Marines",
            "Space Wolves",
            "Champions of Fenris, Legends of Saga and Song and Veterans of the Fang"
            " (3 Detachment Points)",
            "Disruption",
            "Strike Force (2,000 Points)",
        ],
        army_list,
    )

    assert army_list.super_faction == "Space Marines"
    assert army_list.faction == "Space Wolves"
    assert army_list.detachments == [
        "Champions of Fenris",
        "Legends of Saga and Song",
        "Veterans of the Fang",
    ]
    assert army_list.detachment_points == 3
    assert army_list.disposition == "Disruption"
    assert army_list.army_size == "Strike Force"
    assert army_list.army_size_points == 2000


def test_faction_only_header_leaves_disposition_empty():
    army_list = ArmyList()
    parse_header(
        [
            "T’au Empire",
            "Retaliation Cadre (3 Detachment Points)",
            "Strike Force (2,000 Points)",
        ],
        army_list,
    )

    assert army_list.faction == "T’au Empire"
    assert army_list.disposition == ""


@pytest.mark.parametrize(
    "line,expected",
    [
        ("Retaliation Cadre", ["Retaliation Cadre"]),
        # A single detachment whose own name contains "and" is never split.
        ("Legends of Saga and Song", ["Legends of Saga and Song"]),
        (
            "Champions of Fenris, Legends of Saga and Song and Veterans of the Fang",
            [
                "Champions of Fenris",
                "Legends of Saga and Song",
                "Veterans of the Fang",
            ],
        ),
        (
            "Champions of Fenris, Veterans of the Fang",
            ["Champions of Fenris", "Veterans of the Fang"],
        ),
    ],
)
def test_split_detachments(line, expected):
    assert split_detachments(line) == expected


def test_missing_army_size_line_raises():
    with pytest.raises(ParseError):
        parse_header(
            [
                "T’au Empire",
                "Retaliation Cadre (3 Detachment Points)",
                "Purge the Foe",
            ],
            ArmyList(),
        )


def test_missing_detachment_line_raises():
    with pytest.raises(ParseError):
        parse_header(
            ["T’au Empire", "Purge the Foe", "Strike Force (2,000 Points)"],
            ArmyList(),
        )


def test_too_many_faction_lines_raises():
    with pytest.raises(ParseError):
        parse_header(
            [
                "One",
                "Two",
                "Three",
                "Four",
                "Retaliation Cadre (3 Detachment Points)",
                "Strike Force (2,000 Points)",
            ],
            ArmyList(),
        )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest src/tests/test_official_app_header.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'listgrok.parsers.official_app.header'`.

- [ ] **Step 3: Write the implementation**

Create `src/listgrok/parsers/official_app/header.py`:

```python
"""Parse the metadata block of an 11th edition official-app export.

The two labelled lines are found by pattern, not position, because the app has
moved them between dialects before. What remains maps by order.
"""

from listgrok.army.army_list import ArmyList
from listgrok.parsers.official_app.blocks import (
    DETACHMENT_REGEX,
    POINTS_REGEX,
    parse_points,
)
from listgrok.parsers.parse_error import ParseError


def split_detachments(text: str) -> list[str]:
    """Split a detachment line into individual detachment names.

    Several detachments are written as a serial list: "A, B and C". Names
    themselves contain "and" ("Legends of Saga and Song"), so only the final
    comma-separated segment is split, on its last " and ". A line with no comma
    is never split, which means a two-detachment line written without one
    ("A and B") comes back as a single detachment — the export carries no signal
    that would let us tell that apart from one detachment named "A and B".
    """
    parts = [part.strip() for part in text.split(",")]
    if len(parts) == 1:
        return parts

    tail = parts.pop()
    head, separator, last = tail.rpartition(" and ")
    if separator:
        parts.extend([head.strip(), last.strip()])
    else:
        parts.append(tail)
    return parts


def parse_header(lines: list[str], army_list: ArmyList) -> None:
    """Assign the army's faction metadata from the header block, in place."""
    lines = [line.strip() for line in lines]
    # Filter on the iteration variable rather than a walrus in the `if` clause,
    # so the type checker can narrow away the None.
    size_matches = [m for m in (POINTS_REGEX.match(line) for line in lines) if m]
    detachment_matches = [
        m for m in (DETACHMENT_REGEX.match(line) for line in lines) if m
    ]

    if len(size_matches) != 1:
        raise ParseError(
            f"Expected exactly one army-size line, found {len(size_matches)}", lines
        )
    if len(detachment_matches) != 1:
        raise ParseError(
            f"Expected exactly one detachment line, found {len(detachment_matches)}",
            lines,
        )

    size, detachment = size_matches[0], detachment_matches[0]
    army_list.army_size = size.group("name")
    army_list.army_size_points = parse_points(size.group("points"))
    army_list.detachments = split_detachments(detachment.group("name"))
    army_list.detachment_points = int(detachment.group("points"))

    consumed = {size.group(0), detachment.group(0)}
    rest = [line for line in lines if line not in consumed]

    if len(rest) == 3:
        army_list.super_faction, army_list.faction, army_list.disposition = rest
    elif len(rest) == 2:
        army_list.faction, army_list.disposition = rest
    elif len(rest) == 1:
        army_list.faction = rest[0]
    else:
        raise ParseError(f"Expected 1 to 3 faction lines, found {len(rest)}", lines)
```

`DETACHMENT_REGEX` cannot be confused with `POINTS_REGEX`: the latter requires
the digits to be followed immediately by ` Points)`, and a detachment line has
` Detachment ` in between.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest src/tests/test_official_app_header.py -q`
Expected: 10 passed.

- [ ] **Step 5: Lint and typecheck**

Run: `make test && make lint && make typecheck`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/listgrok/parsers/official_app/header.py src/tests/test_official_app_header.py
git commit -m "Parse the 11th edition metadata block

Finds the army-size and detachment lines by pattern and maps the rest by
order, so super-faction is optional. Detachment splitting only fires on the
final segment of a comma list, leaving names that contain 'and' intact."
```

---

### Task 5: Unit blocks (`units.py`)

**Files:**
- Create: `src/listgrok/parsers/official_app/units.py`
- Test: `src/tests/test_official_app_units.py`

**Interfaces:**
- Consumes: `POINTS_REGEX`, `NUM_REGEX`, `ATTACHED_AS_REGEX`, `BULLET_REGEX`, `parse_points` from `blocks.py`; `Attachment`, `Unit`, `UnitComposition`; `ParseError`.
- Produces:
  - `Node` — dataclass with `text: str`, `indent: int`, `children: list[Node]`
  - `build_tree(body_lines: list[str]) -> list[Node]`
  - `parse_unit(lines: list[str], sheet_type: str) -> Unit`

- [ ] **Step 1: Write the failing tests**

Create `src/tests/test_official_app_units.py`:

```python
import pytest

from listgrok.parsers.official_app.units import build_tree, parse_unit
from listgrok.parsers.parse_error import ParseError


class TestBuildTree:
    def test_flat_body_has_no_children(self):
        # official_1 Ghostkeel Battlesuit
        roots = build_tree(
            [
                "  • 1x Battlesuit Support System",
                "  • 1x Fusion collider",
                "  • 1x Ghostkeel fists",
            ]
        )

        assert [node.text for node in roots] == [
            "1x Battlesuit Support System",
            "1x Fusion collider",
            "1x Ghostkeel fists",
        ]
        assert all(node.children == [] for node in roots)

    def test_deeper_indent_nests(self):
        # official_1 Vespid Stingwings
        roots = build_tree(
            [
                "  • 1x Vespid Strain Leader",
                "     ◦ 1x Neutron blaster",
                "     ◦ 1x Stingwing claws",
                "  • 4x Vespid Stingwing",
                "     ◦ 4x Neutron blaster",
            ]
        )

        assert len(roots) == 2
        assert roots[0].text == "1x Vespid Strain Leader"
        assert [child.text for child in roots[0].children] == [
            "1x Neutron blaster",
            "1x Stingwing claws",
        ]
        assert roots[1].text == "4x Vespid Stingwing"
        assert [child.text for child in roots[1].children] == ["4x Neutron blaster"]


class TestParseUnit:
    def test_single_model_unit_gets_one_implicit_model_set(self):
        # official_1 Ghostkeel Battlesuit
        unit = parse_unit(
            [
                "Ghostkeel Battlesuit (150 Points)",
                "  • 1x Battlesuit Support System",
                "  • 1x Fusion collider",
                "  • 1x Ghostkeel fists",
                "  • 1x Twin fusion blaster",
            ],
            "OTHER DATASHEETS",
        )

        assert unit.name == "Ghostkeel Battlesuit"
        assert unit.points == 150
        assert unit.sheet_type == "OTHER DATASHEETS"
        assert unit.attachment is None
        assert len(unit.composition) == 1
        assert unit.composition[0].name == "Ghostkeel Battlesuit"
        assert unit.composition[0].num_models == 1
        assert unit.composition[0].wargear == {
            "Battlesuit Support System": 1,
            "Fusion collider": 1,
            "Ghostkeel fists": 1,
            "Twin fusion blaster": 1,
        }

    def test_multi_model_unit_gets_one_model_set_per_root(self):
        # official_1 Kroot Carnivores
        unit = parse_unit(
            [
                "Kroot Carnivores (65 Points)",
                "  • 1x Long-quill",
                "     ◦ 1x Close combat weapon",
                "     ◦ 1x Kroot pistol",
                "     ◦ 1x Kroot rifle",
                "  • 9x Kroot Carnivore",
                "     ◦ 9x Close combat weapon",
                "     ◦ 9x Kroot rifle",
            ],
            "OTHER DATASHEETS",
        )

        assert len(unit.composition) == 2
        assert unit.composition[0].name == "Long-quill"
        assert unit.composition[0].num_models == 1
        assert unit.composition[0].wargear == {
            "Close combat weapon": 1,
            "Kroot pistol": 1,
            "Kroot rifle": 1,
        }
        assert unit.composition[1].name == "Kroot Carnivore"
        assert unit.composition[1].num_models == 9
        assert unit.composition[1].wargear == {
            "Close combat weapon": 9,
            "Kroot rifle": 9,
        }

    def test_warlord_and_attachment_and_repeated_wargear(self):
        # official_1 Commander in Enforcer Battlesuit: the app writes the four
        # missile pods as two lines.
        unit = parse_unit(
            [
                "Commander in Enforcer Battlesuit (80 Points)",
                "  • Attached as: Leader (Character)",
                "  • Warlord",
                "  • 1x Battlesuit fists",
                "  • 1x Missile pod",
                "  • 3x Missile pod",
                "  • 2x Shield Drone",
            ],
            "ATTACHED UNITS",
        )

        assert unit.is_warlord
        assert unit.attachment is not None
        assert unit.attachment.role == "Leader"
        assert unit.attachment.role_detail == "Character"
        assert unit.attachment.group == ""  # stamped by the fold, not here
        assert unit.composition[0].wargear == {
            "Battlesuit fists": 1,
            "Missile pod": 4,
            "Shield Drone": 2,
        }

    def test_bodyguard_attachment_with_empty_detail(self):
        # official_1 Crisis Fireknife Battlesuits
        unit = parse_unit(
            [
                "Crisis Fireknife Battlesuits (130 Points)",
                "  • Attached as: Bodyguard ()",
                "  • 1x Crisis Fireknife Shas’vre",
                "     ◦ 1x Battlesuit fists",
                "  • 2x Crisis Fireknife Shas’ui",
                "     ◦ 2x Battlesuit fists",
            ],
            "ATTACHED UNITS",
        )

        assert unit.attachment is not None
        assert unit.attachment.role == "Bodyguard"
        assert unit.attachment.role_detail == ""
        assert len(unit.composition) == 2

    def test_enhancement_keeps_its_parenthetical(self):
        # official_2 Captain in Terminator Armour
        unit = parse_unit(
            [
                "Captain in Terminator Armour (100 Points)",
                "  • 1x Combi-weapon",
                "  • 1x Relic fist",
                "  • Enhancements: Thirst for Glory (Upgrade)",
            ],
            "CHARACTERS",
        )

        assert unit.enhancement == "Thirst for Glory (Upgrade)"
        assert unit.composition[0].wargear == {"Combi-weapon": 1, "Relic fist": 1}

    def test_singular_enhancement_label_is_accepted(self):
        unit = parse_unit(
            [
                "Captain in Terminator Armour (100 Points)",
                "  • 1x Combi-weapon",
                "  • Enhancement: Thirst for Glory",
            ],
            "CHARACTERS",
        )

        assert unit.enhancement == "Thirst for Glory"

    def test_unrecognised_body_line_becomes_a_decoration(self):
        # Synthetic: no 11th fixture has one yet, but 10th ed exports carried
        # lines like this and the model keeps an escape hatch for them.
        unit = parse_unit(
            [
                "Ghostkeel Battlesuit (150 Points)",
                "  • Daemonic Allegiance: Tzeentch",
                "  • 1x Ghostkeel fists",
            ],
            "OTHER DATASHEETS",
        )

        assert unit.decorations == ["Daemonic Allegiance: Tzeentch"]
        assert unit.composition[0].wargear == {"Ghostkeel fists": 1}

    def test_comma_formatted_unit_points(self):
        unit = parse_unit(["Titanic Thing (1,000 Points)", "  • 1x Big gun"], "CHARACTERS")

        assert unit.points == 1000

    def test_unparseable_header_raises(self):
        with pytest.raises(ParseError):
            parse_unit(["Ghostkeel Battlesuit", "  • 1x Ghostkeel fists"], "CHARACTERS")

    def test_empty_block_raises(self):
        with pytest.raises(ParseError):
            parse_unit([], "CHARACTERS")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest src/tests/test_official_app_units.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'listgrok.parsers.official_app.units'`.

- [ ] **Step 3: Write the implementation**

Create `src/listgrok/parsers/official_app/units.py`:

```python
"""Parse a unit block of an 11th edition official-app export.

Indentation is authoritative. Bullet glyphs are stripped and the leading-space
count decides nesting, so a body line indented deeper than the line above it is
that line's child.
"""

from dataclasses import dataclass, field

from listgrok.army.army_list import Attachment, Unit, UnitComposition
from listgrok.parsers.official_app.blocks import (
    ATTACHED_AS_REGEX,
    BULLET_REGEX,
    NUM_REGEX,
    POINTS_REGEX,
    parse_points,
)
from listgrok.parsers.parse_error import ParseError

WARLORD_LINE = "Warlord"
ENHANCEMENT_PREFIXES = ("Enhancements:", "Enhancement:")


@dataclass
class Node:
    text: str
    indent: int
    children: list["Node"] = field(default_factory=list)


def build_tree(body_lines: list[str]) -> list[Node]:
    """Build the indentation forest for a unit block's body (header excluded)."""
    roots: list[Node] = []
    stack: list[Node] = []

    for raw in body_lines:
        indent = len(raw) - len(raw.lstrip())
        node = Node(text=BULLET_REGEX.sub("", raw.strip()), indent=indent)

        while stack and stack[-1].indent >= indent:
            stack.pop()
        (stack[-1].children if stack else roots).append(node)
        stack.append(node)

    return roots


def parse_unit(lines: list[str], sheet_type: str) -> Unit:
    if not lines:
        raise ParseError("Empty unit block", lines)

    header = POINTS_REGEX.match(lines[0].strip())
    if header is None:
        raise ParseError("Unexpected unit header", lines)

    unit = Unit(
        name=header.group("name"),
        points=parse_points(header.group("points")),
        sheet_type=sheet_type,
    )
    _populate(unit, build_tree(lines[1:]))
    return unit


def _populate(unit: Unit, roots: list[Node]) -> None:
    models: list[Node] = []
    for node in roots:
        if node.text == WARLORD_LINE:
            unit.is_warlord = True
        elif node.text.startswith(ENHANCEMENT_PREFIXES):
            unit.enhancement = node.text.split(":", 1)[1].strip()
        elif (match := ATTACHED_AS_REGEX.match(node.text)) is not None:
            unit.attachment = Attachment(
                role=match.group("role").strip(),
                role_detail=match.group("detail").strip(),
            )
        else:
            models.append(node)

    # Nested children mean each root is a model set with its wargear beneath.
    # A flat body means one implicit model set holding all of the wargear.
    if any(node.children for node in models):
        for node in models:
            model_set = _model_set_from(node.text)
            unit.add_model_set(model_set)
            for child in node.children:
                _add_wargear(unit, model_set, child.text)
    else:
        model_set = UnitComposition(name=unit.name, num_models=1)
        unit.add_model_set(model_set)
        for node in models:
            _add_wargear(unit, model_set, node.text)


def _model_set_from(text: str) -> UnitComposition:
    if (match := NUM_REGEX.match(text)) is not None:
        return UnitComposition(
            name=match.group("name"), num_models=int(match.group("num"))
        )
    return UnitComposition(name=text)


def _add_wargear(unit: Unit, model_set: UnitComposition, text: str) -> None:
    if (match := NUM_REGEX.match(text)) is not None:
        model_set.add_wargear(match.group("name"), int(match.group("num")))
    else:
        unit.decorations.append(text)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest src/tests/test_official_app_units.py -q`
Expected: 12 passed.

- [ ] **Step 5: Lint and typecheck**

Run: `make test && make lint && make typecheck`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/listgrok/parsers/official_app/units.py src/tests/test_official_app_units.py
git commit -m "Parse 11th edition unit blocks

Body lines become an indentation forest; a root with children is a model set
with its wargear beneath it, and a flat body collapses into one implicit model
set. Warlord, Enhancements and the new 'Attached as:' line are lifted off the
roots first; repeated wargear names sum."
```

---

### Task 6: Fold the stream into an `ArmyList` and restore dispatch

**Files:**
- Modify: `src/listgrok/parsers/official_app/__init__.py`
- Modify: `src/listgrok/parse_list.py`
- Test: `src/tests/test_official_app.py` (create), `src/tests/test_parse_list.py` (create)

**Interfaces:**
- Consumes: `BlockKind`, `classify_blocks`, `POINTS_REGEX`, `parse_points` from `blocks.py`; `parse_header` from `header.py`; `parse_unit` from `units.py`; `Attachment`, `ArmyList`.
- Produces: `parse_official_app(list_text: str) -> ArmyList`, importable as `from listgrok.parsers.official_app import parse_official_app`.

- [ ] **Step 1: Write the failing end-to-end tests**

Create `src/tests/test_official_app.py`:

```python
from pathlib import Path

import pytest

from listgrok.parsers.official_app import parse_official_app

EXAMPLES = Path(__file__).parents[2] / "examples" / "official_app"

OFFICIAL_EXAMPLES = {
    "official_1.txt": {
        "name": "11th stuff",
        "points": 2000,
        "super_faction": "",
        "faction": "T’au Empire",
        "detachments": ["Retaliation Cadre"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 18,
        "attached_groups": 4,
    },
    "official_2.txt": {
        "name": "Awoo",
        "points": 1260,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": [
            "Champions of Fenris",
            "Legends of Saga and Song",
            "Veterans of the Fang",
        ],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 9,
        "attached_groups": 1,
    },
}


def parse_example(filename: str):
    return parse_official_app((EXAMPLES / filename).read_text())


class TestAllOfficialExamples:
    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_metadata(self, filename):
        expected = OFFICIAL_EXAMPLES[filename]
        army_list = parse_example(filename)

        assert army_list.name == expected["name"]
        assert army_list.points == expected["points"]
        assert army_list.super_faction == expected["super_faction"]
        assert army_list.faction == expected["faction"]
        assert army_list.detachments == expected["detachments"]
        assert army_list.detachment_points == expected["detachment_points"]
        assert army_list.disposition == expected["disposition"]
        assert army_list.army_size == expected["army_size"]
        assert army_list.army_size_points == expected["army_size_points"]
        assert len(army_list.units) == expected["unit_count"]

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_units_are_well_formed(self, filename):
        army_list = parse_example(filename)

        for unit in army_list.units:
            assert unit.name, f"{filename}: unit with empty name"
            assert isinstance(unit.points, int)
            assert unit.sheet_type, f"{filename}: {unit.name} has no sheet type"
            assert unit.composition, f"{filename}: {unit.name} has no composition"
            for model_set in unit.composition:
                assert model_set.name, f"{filename}: {unit.name} model set unnamed"
                assert all(count > 0 for count in model_set.wargear.values())

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_unit_points_sum_to_the_list_total(self, filename):
        army_list = parse_example(filename)

        assert sum(unit.points or 0 for unit in army_list.units) == army_list.points

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_attached_units_pair_a_leader_with_a_bodyguard(self, filename):
        army_list = parse_example(filename)

        groups: dict[str, list[str]] = {}
        for unit in army_list.units:
            if unit.attachment is not None:
                groups.setdefault(unit.attachment.group, []).append(
                    unit.attachment.role
                )

        assert len(groups) == OFFICIAL_EXAMPLES[filename]["attached_groups"]
        for group, roles in groups.items():
            assert group.startswith("Attached unit "), group
            assert sorted(roles) == ["Bodyguard", "Leader"]

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_unattached_units_have_no_attachment(self, filename):
        army_list = parse_example(filename)

        for unit in army_list.units:
            if unit.sheet_type != "ATTACHED UNITS":
                assert unit.attachment is None, unit.name


class TestOfficial1Details:
    def test_warlord_is_the_enforcer_commander(self):
        army_list = parse_example("official_1.txt")

        warlords = [unit.name for unit in army_list.units if unit.is_warlord]
        assert warlords == ["Commander in Enforcer Battlesuit"]

    def test_enhancement_is_read_from_an_attached_unit(self):
        army_list = parse_example("official_1.txt")

        enhanced = {
            unit.name: unit.enhancement for unit in army_list.units if unit.enhancement
        }
        assert enhanced == {"Commander in Coldstar Battlesuit": "Prototype Weapon System"}

    def test_character_with_two_named_models(self):
        # "The Twin Lance" is a CHARACTERS entry with two model sets.
        army_list = parse_example("official_1.txt")

        twins = next(u for u in army_list.units if u.name == "The Twin Lance")
        assert twins.sheet_type == "CHARACTERS"
        assert [model_set.name for model_set in twins.composition] == [
            "Ri’Lantar",
            "Ri’Locai",
        ]


class TestOfficial2Details:
    def test_sheet_types(self):
        army_list = parse_example("official_2.txt")

        counts: dict[str, int] = {}
        for unit in army_list.units:
            counts[unit.sheet_type] = counts.get(unit.sheet_type, 0) + 1

        assert counts == {"ATTACHED UNITS": 2, "CHARACTERS": 6, "OTHER DATASHEETS": 1}

    def test_bodyguard_carries_its_battleline_detail(self):
        army_list = parse_example("official_2.txt")

        blood_claws = next(u for u in army_list.units if u.name == "Blood Claws")
        assert blood_claws.attachment is not None
        assert blood_claws.attachment.role == "Bodyguard"
        assert blood_claws.attachment.role_detail == "Battleline"
        assert blood_claws.attachment.group == "Attached unit 1"
```

Create `src/tests/test_parse_list.py`:

```python
from pathlib import Path

from listgrok import parse_list

EXAMPLES = Path(__file__).parents[2] / "examples"


def test_official_app_export_routes_to_the_official_app_parser():
    army_list = parse_list((EXAMPLES / "official_app" / "official_1.txt").read_text())

    assert army_list.faction == "T’au Empire"
    assert army_list.disposition == "Purge the Foe"


def test_new_recruit_export_falls_back_to_the_new_recruit_parser():
    army_list = parse_list((EXAMPLES / "nr" / "nr1_gw.txt").read_text())

    # Note the plain ASCII apostrophe: the NewRecruit fixture uses U+0027 where
    # the official-app fixtures use the typographic U+2019.
    assert army_list.faction == "Xenos - T'au Empire"
    assert army_list.detachments == ["Experimental Prototype Cadre"]
    assert army_list.disposition == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest src/tests/test_official_app.py src/tests/test_parse_list.py -q`
Expected: FAIL — `ImportError: cannot import name 'parse_official_app'`.

- [ ] **Step 3: Write the fold**

Replace the contents of `src/listgrok/parsers/official_app/__init__.py` with:

```python
"""Parse army lists exported from GW's official Warhammer 40k app (11th edition).

The export is folded from a classified block stream into an ArmyList, carrying
only the current sheet type and the current attachment group as state.
"""

from listgrok.army.army_list import ArmyList, Attachment, Unit
from listgrok.parsers.official_app.blocks import (
    POINTS_REGEX,
    BlockKind,
    classify_blocks,
    parse_points,
)
from listgrok.parsers.official_app.header import parse_header
from listgrok.parsers.official_app.units import parse_unit
from listgrok.parsers.parse_error import ParseError

__all__ = ["parse_official_app"]


def parse_official_app(list_text: str) -> ArmyList:
    army_list = ArmyList()
    sheet_type = ""
    group = ""

    for block in classify_blocks(list_text):
        if block.kind is BlockKind.ARMY_NAME:
            _parse_army_name(block.lines, army_list)
        elif block.kind is BlockKind.HEADER:
            parse_header(block.lines, army_list)
        elif block.kind is BlockKind.SECTION:
            sheet_type = block.lines[0].strip()
            group = ""
        elif block.kind is BlockKind.GROUP:
            group = block.lines[0].strip()
        elif block.kind is BlockKind.UNIT:
            army_list.add_unit(_parse_unit_in(block.lines, sheet_type, group))

    return army_list


def _parse_army_name(lines: list[str], army_list: ArmyList) -> None:
    match = POINTS_REGEX.match("\n".join(lines).strip())
    if match is None:
        raise ParseError("Unexpected army-name block", lines)
    army_list.name = match.group("name")
    army_list.points = parse_points(match.group("points"))


def _parse_unit_in(lines: list[str], sheet_type: str, group: str) -> Unit:
    """Parse a unit block and stamp the enclosing attachment group onto it.

    A unit under a group heading is attached even if it carries no
    "Attached as:" line; a unit outside one keeps attachment = None.
    """
    unit = parse_unit(lines, sheet_type)
    if group:
        if unit.attachment is None:
            unit.attachment = Attachment()
        unit.attachment.group = group
    return unit
```

- [ ] **Step 4: Restore dispatch in `parse_list`**

Replace the entire contents of `src/listgrok/parse_list.py` with:

```python
from listgrok.army.army_list import ArmyList
from listgrok.parsers.new_recruit_gw import NewRecruitGWParser
from listgrok.parsers.official_app import parse_official_app
from listgrok.parsers.parse_error import ParseError


def parse_list(list_text: str) -> ArmyList:
    try:
        return parse_official_app(list_text)
    except ParseError:
        return NewRecruitGWParser().parse(list_text)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest src/tests/test_official_app.py src/tests/test_parse_list.py -q`
Expected: all passed.

If `test_unit_points_sum_to_the_list_total` fails, do **not** relax the
assertion — both fixtures were checked by hand and do sum exactly (2000 and
1260). A mismatch means units are being dropped or double-counted.

- [ ] **Step 6: Run the whole suite plus lint and types**

Run: `make test && make lint && make typecheck`
Expected: all green.

- [ ] **Step 7: Verify the manual smoke script works again**

Run: `uv run python examples/examples.py`
Expected: prints a parsed `ArmyList` for each of the two fixtures, with
`disposition` and `detachments` populated. This is the script Task 1 knowingly
broke.

- [ ] **Step 8: Commit**

```bash
git add src/listgrok/parsers/official_app/__init__.py src/listgrok/parse_list.py \
        src/tests/test_official_app.py src/tests/test_parse_list.py
git commit -m "Fold classified blocks into an ArmyList and restore dispatch

parse_official_app walks the block stream carrying only the current sheet type
and attachment group, stamping the group onto each attached unit. parse_list
tries it first and falls back to NewRecruit on ParseError."
```

---

### Task 7: Update the documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `pyproject.toml:4`
- Modify: `README.md:11`

**Interfaces:**
- Consumes: the finished parser.
- Produces: nothing importable.

- [ ] **Step 1: Update the project description**

In `pyproject.toml`, change line 4 from:

```toml
description = "Warhammer 40k 10th edition list parser"
```

to:

```toml
description = "Warhammer 40k 11th edition list parser"
```

- [ ] **Step 2: Rewrite the CLAUDE.md Overview line**

Change:

> listgrok is a zero-dependency library that parses Warhammer 40k 10th edition army lists (text exported from various army-builder apps) into a common data model. Early development: APIs are unstable.

to:

> listgrok is a zero-dependency library that parses Warhammer 40k 11th edition army lists (text exported from various army-builder apps) into a common data model. Early development: APIs are unstable.

- [ ] **Step 3: Replace the Architecture section**

Replace everything in `CLAUDE.md` from `**Entry point.**` through the end of the
`### new_recruit_gw.py (NewRecruit "GW" export)` subsection with:

````markdown
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
````

- [ ] **Step 4: Update the "Fixtures are the spec" section**

Change the sentence naming the test file so it reads:

> When adding a new export sample, add an entry to `OFFICIAL_EXAMPLES` in `src/tests/test_official_app.py` — the parametrized `TestAllOfficialExamples` checks faction metadata and unit count for every file listed there, asserts all units are well-formed, and asserts the units' points sum to the list total. Unit tests in `test_official_app_blocks.py`, `test_official_app_header.py` and `test_official_app_units.py` state which example file each case came from; keep that convention when adding cases.

- [ ] **Step 5: Name the supported edition in the README**

In `README.md`, change line 11 from:

```markdown
- [x] Official GW 40k app
```

to:

```markdown
- [x] Official GW 40k app (11th edition)
```

Leave the rest of `README.md` alone — it documents no `ArmyList` fields, so the
data model change does not reach it.

- [ ] **Step 6: Verify the docs match reality**

Run: `make test && make lint && make typecheck`
Expected: all green. Then re-read the rewritten Architecture section against
`src/listgrok/parsers/official_app/` and confirm every module and function it
names exists with that name.

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md pyproject.toml README.md
git commit -m "Document the 11th edition parser

Rewrites the Architecture section for the classify-then-fold package and the
extended data model, and drops the 10th ed dialect notes."
```

---

## Verification checklist

After Task 7, all of the following must hold:

- [ ] `make test` — all green, no skips
- [ ] `make lint` — clean
- [ ] `make typecheck` — clean
- [ ] `uv run python examples/examples.py` — parses both fixtures
- [ ] `git status` — clean tree; `examples/official_app/*.txt` tracked
- [ ] `grep -rn "10th edition" CLAUDE.md pyproject.toml README.md` — only in
      historical context, if at all
- [ ] `grep -rn --include='*.py' "\.detachment\b" src/` — no output
- [ ] `src/listgrok/parsers/official_app.py` no longer exists
