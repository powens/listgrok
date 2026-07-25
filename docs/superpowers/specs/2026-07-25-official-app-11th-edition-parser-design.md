# Official App 11th Edition Parser — Design

Date: 2026-07-25

## Goal

Replace the 10th edition GW official-app parser with a greenfield parser for the
11th edition export format. The 11th format adds attached units (a leader
datasheet and a bodyguard datasheet fighting as one unit), a disposition line,
detachment points, multiple detachments per list, and comma-formatted point
totals. None of these fit the 10th ed data model or its line-by-line state
machine.

10th edition support is dropped entirely. Its example fixtures were already
deleted in commit `4c1b7bc`, which is why `pytest` currently reports 18
failures.

## Format

Two real exports drive the design, both `App Version: v2.3.0 (1), Data Version:
v912`:

- `examples/official_app/official_1.txt` — T'au Empire, no super-faction, 4
  attached-unit groups, 18 units, 2000 points.
- `examples/official_app/official_2.txt` — Space Wolves under a Space Marines
  super-faction, 3 detachments on one line, 1 attached-unit group, 9 units,
  1260 of 2000 points.

Both are committed as part of this work (they are untracked today).

Document shape:

```
Awoo (1,260 Points)                                     <- army name + points

Space Marines                                           <- super-faction
Space Wolves                                            <- faction
Champions of Fenris, Legends of Saga and Song
  and Veterans of the Fang (3 Detachment Points)        <- detachments + points
Disruption                                              <- disposition
Strike Force (2,000 Points)                             <- army size + cap

ATTACHED UNITS                                          <- section heading

Attached unit 1                                         <- group heading

Ragnar Blackmane (90 Points)
  • Attached as: Leader (Character)
  • 1x Bolt Pistol

Blood Claws (135 Points)
  • Attached as: Bodyguard (Battleline)
  • 1x Blood Claw Pack Leader
     ◦ 1x Astartes chainsword
  • 9x Blood Claw
     ◦ 9x Astartes chainsword

CHARACTERS                                              <- section heading

Logan Grimnar (100 Points)
  • Warlord
  • 1x Axe Morkai

Captain in Terminator Armour (100 Points)
  • 1x Combi-weapon
  • Enhancements: Thirst for Glory (Upgrade)

OTHER DATASHEETS

...

Exported with App Version: v2.3.0 (1), Data Version: v912   <- trailer
```

Deltas from 10th edition:

1. Point totals may carry thousands commas (`2,000 Points`). The 10th
   `POINTS_LABEL_REGEX` uses `\d+` and cannot match them.
2. The detachment line carries a `(N Detachment Points)` suffix and may name
   several detachments.
3. A disposition line (`Purge the Foe`, `Disruption`) sits between the
   detachment and army-size lines.
4. An `ATTACHED UNITS` section contains `Attached unit N` group headings, each
   grouping two or more datasheets.
5. Units inside a group carry an `Attached as: <role> (<detail>)` line, where
   detail may be empty: `Bodyguard ()`.
6. The same wargear name can appear on two body lines of one model set with
   different counts (`1x Missile pod` and `3x Missile pod`).

## Data model (`src/listgrok/army/army_list.py`)

```python
@dataclass
class Attachment:
    group: str = ""          # "Attached unit 1" — verbatim group heading
    role: str = ""           # "Leader" | "Bodyguard"
    role_detail: str = ""    # "Character" | "Battleline" | ""

@dataclass
class UnitComposition:       # unchanged
    name: str = ""
    num_models: int | None = None
    wargear: dict[str, int] = field(default_factory=dict)

@dataclass
class Unit:
    name: str = ""
    sheet_type: str = ""                     # "ATTACHED UNITS" | "CHARACTERS" | ...
    is_warlord: bool = False
    enhancement: str = ""                    # "Thirst for Glory (Upgrade)"
    points: int | None = None
    composition: list[UnitComposition] = field(default_factory=list)
    decorations: list[str] = field(default_factory=list)
    attachment: Attachment | None = None     # NEW

@dataclass
class ArmyList:
    name: str = ""
    points: int | None = None                # 1260
    super_faction: str = ""                  # "Space Marines"
    faction: str = ""                        # "Space Wolves"
    detachments: list[str] = field(default_factory=list)   # NEW, replaces detachment: str
    detachment_points: int | None = None     # NEW — 3
    disposition: str = ""                    # NEW — "Disruption"
    army_size: str = ""                      # "Strike Force" (name only)
    army_size_points: int | None = None      # NEW — 2000
    units: list[Unit] = field(default_factory=list)
```

Decisions:

- **Attached units stay in one flat `units` list**, in file order, tagged with
  `attachment`. Grouping is derivable by `attachment.group`. A nested model
  (leader owns bodyguards) was rejected: it breaks on a group with no leader or
  several leaders, and forces consumers to recurse to enumerate datasheets.
- **`enhancement` keeps the text verbatim**, including the `(Upgrade)`
  parenthetical, since stripping it loses information the parser cannot
  reconstruct.
- **Repeated wargear names sum.** `wargear` stays `dict[str, int]`, so the
  Enforcer Commander's `1x` + `3x Missile pod` becomes `{"Missile pod": 4}`.
  The split is treated as an app artifact.
- **`army_size` splits** into a name and a points cap so callers can compare
  `points` against `army_size_points` without re-parsing a string.
- `add_unit`, `add_model_set` and `add_wargear` survive unchanged;
  `add_wargear` is what implements the sum-by-name rule.
- `to_json()` on every dataclass. `super_faction`, `is_warlord` and
  `attachment` are omitted when unset (matching how `is_warlord` is handled
  today); all other fields are always emitted.

This breaks `ArmyList`'s shape (`detachment` → `detachments`, `army_size`
semantics). CLAUDE.md states the API is explicitly unstable, and nothing
in-repo depends on the old shape once 10th ed is removed.

## Architecture

Classify, then fold. Two passes with a typed boundary between them:

```
text ──split/classify──▶ [Block] ──fold──▶ ArmyList
                                    │
              UnitBlock ──▶ indent tree ──▶ Unit
```

The 10th ed parser collapsed document, unit and body grammars into one
line-by-line state machine, which is why `_handle_start` had to return `False`
so the caller could re-read a block as something else. Making classification an
explicit first stage removes that: an export with no army-name header is simply
a block stream that starts with `HEADER`.

Layout:

```
src/listgrok/parsers/
  official_app/
    __init__.py   # parse_official_app — the fold
    blocks.py     # text -> classified block stream
    header.py     # header block -> army metadata
    units.py      # unit block -> Unit (indent tree)
  new_recruit_gw.py
  parse_error.py
  helpers.py
```

Each module is independently testable without constructing the others.

### `blocks.py`

```python
class BlockKind(Enum):
    ARMY_NAME, HEADER, SECTION, GROUP, UNIT, TRAILER

@dataclass(frozen=True)
class Block:
    kind: BlockKind
    lines: list[str]

def classify_blocks(text: str) -> list[Block]: ...
```

Split on blank lines, drop empties, classify each block by shape:

| Rule | Kind |
|---|---|
| First line starts with `Exported with App Version:` | `TRAILER` |
| Contains a `(N Detachment Points)` line | `HEADER` |
| Points-labelled when joined, before the header | `ARMY_NAME` |
| First line points-labelled, after the header | `UNIT` |
| Single line, ALL CAPS | `SECTION` |
| Single line, otherwise | `GROUP` |
| anything else | raise `ParseError` |

The header signature is the detachment-points line: the metadata block is the
only block that carries one, which makes it unmistakable without consulting
position. Everything before it is the army name, everything after is sections,
groups and units. Classification is a single pass carrying one boolean (header
seen yet), so `ARMY_NAME` and `UNIT` stay distinguishable without lookahead or
backtracking.

`ARMY_NAME` matches against the block's lines joined with `\n`, and
`POINTS_REGEX` is compiled `re.DOTALL`, so a multi-line army name still yields
one name. Keying `HEADER` off the detachment line rather than off "the points
line is not first" is what makes that possible: under the latter rule a
multi-line army name has exactly the header's shape and would be swallowed by
it.

Patterns live in this module:

```python
POINTS_REGEX      = r"^(?P<name>.+?)\s\((?P<points>[\d,]+)\s[Pp]oints\)$"  # re.DOTALL
DETACHMENT_REGEX  = r"^(?P<name>.+?)\s\((?P<points>\d+)\sDetachment\s[Pp]oints?\)$"
NUM_REGEX         = r"^(?P<num>\d+)x\s(?P<name>.+)$"
ATTACHED_AS_REGEX = r"^Attached as:\s*(?P<role>[^(]+?)\s*\((?P<detail>[^)]*)\)$"
BULLET_REGEX      = r"^[•◦]\s*"
```

`POINTS_REGEX` accepts thousands commas and cannot match a detachment line,
because it requires the digits to be followed immediately by ` Points)`.

### `header.py`

Locate the two labelled lines by pattern rather than by position: the army-size
line via `POINTS_REGEX`, the detachment line via `DETACHMENT_REGEX`. Exactly one
of each is required; otherwise raise `ParseError` carrying the block.
Classification already guarantees at least one detachment line, so in practice
this rejects a block with two of them, or with zero or several army-size lines.
The detachment line is also what keeps the remaining lines unambiguous —
without its `(N Detachment Points)` suffix a detachment name and a disposition
are indistinguishable, which is why an export lacking it is unsupported rather
than guessed at.

Map the remaining lines in order:

| Remaining | Mapping |
|---|---|
| 3 | `super_faction`, `faction`, `disposition` |
| 2 | `faction`, `disposition` |
| 1 | `faction` |
| other | raise `ParseError` |

Detachment splitting: split on `", "`, then split only the final segment on its
**last** `" and "`. A line containing no comma is never split. This parses
`Champions of Fenris, Legends of Saga and Song and Veterans of the Fang` into
its three real detachments, and leaves a lone `Legends of Saga and Song`
intact.

Known limitation, to be documented in the module docstring: a two-detachment
line written without a comma (`A and B`) is returned as a single detachment.
The export gives the parser no way to tell that apart from one detachment whose
name contains "and".

### `units.py`

Parse the header line with `POINTS_REGEX` for name and points. Build the body
into an indentation tree: strip the bullet glyph, use the raw line's leading
space count as depth, push/pop a stack. There is no bulletless-continuation
special case — 11th bullets every body line, and the 10th ed rule was written
for a dialect no fixture here exhibits.

Dispatch root nodes by content:

- `Warlord` → `is_warlord = True`
- `Enhancement: X` / `Enhancements: X` → `enhancement = X`
- `Attached as: R (D)` → `attachment` role and role detail
- anything else → a model/wargear node

Then: **if any model node has children**, each root is a `UnitComposition`
(count and name from `NUM_REGEX`) with its children as wargear. Otherwise the
unit gets one implicit `UnitComposition` named after the unit with
`num_models = 1`, holding every node as wargear. A node that does not match
`NUM_REGEX` goes to `decorations`.

### `__init__.py` — the fold

Walk the block stream carrying two variables:

```python
sheet_type = ""   # set by SECTION
group      = ""   # set by GROUP, cleared by SECTION
```

- `ARMY_NAME` → `ArmyList.name`, `ArmyList.points`
- `HEADER` → `parse_header`
- `SECTION` → set `sheet_type`, clear `group`
- `GROUP` → set `group`
- `UNIT` → `parse_unit(block, sheet_type)`, stamp `group` onto the unit's
  `Attachment`, append
- `TRAILER` → ignore

A unit under an active group gets an `Attachment` even if it has no
`Attached as:` line (empty `role`). A unit outside any group keeps
`attachment = None`.

### Error handling and dispatch

`parse_error.py` is unchanged: `ParseError(message, block)` carries the
offending block for diagnostics. `parse_list` becomes `parse_official_app`,
falling back to `NewRecruitGWParser().parse` on `ParseError`.

A block stream containing no `HEADER` raises `ParseError`, which doubles as
format detection. No NewRecruit export contains the string `Detachment Points`
(verified across all four `examples/nr/*.txt`), and its point totals read
`1985pts` rather than `(1985 Points)`, so classification fails fast and the
fallback fires. Per CLAUDE.md, a parser must raise rather than return a
half-filled `ArmyList`, or the fallback chain silently produces garbage.

### Strictness posture

Section headings are recognised structurally (a lone ALL-CAPS line), not
against an allow-list, so a future `BATTLELINE` or `ALLIED UNITS` heading lands
in `sheet_type` without a code change. Body lines that are neither `Nx wargear`
nor a known keyword go to `decorations`. `ParseError` is reserved for a
malformed header block, an unparseable unit header, and an unclassifiable
block.

## Testing

`examples/official_app/*.txt` remain the spec. Test files stay flat in
`src/tests/`, mirroring the parser package:

- `test_official_app_blocks.py` — one case per `BlockKind`; the
  detachment-line header signature; a list with no army-name block (stream
  starting with `HEADER`); a multi-line army name still classifying as
  `ARMY_NAME`; a stream with no `HEADER` and an unclassifiable block each
  raising `ParseError`.
- `test_official_app_header.py` — 3-line remainder with super-faction
  (`official_2`); 2-line remainder without (`official_1`); detachment splitting
  (serial-comma list, comma-free name containing "and", single detachment);
  missing army-size line and missing detachment line each raising.
- `test_official_app_units.py` — flat single-model (Ghostkeel); nested
  multi-model (Kroot Carnivores); warlord and enhancement including the
  `(Upgrade)` suffix; `Attached as:` for Leader and for Bodyguard with an empty
  `()`; duplicate wargear summing (`1x` + `3x Missile pod` → 4); decoration
  fallback.
- `test_official_app.py` — end-to-end. An `OFFICIAL_EXAMPLES` table keyed by
  filename carries every metadata field plus unit count, parametrized as today;
  plus well-formedness invariants over all units; plus attachment grouping
  (`official_1` → 4 groups of 2, each one Leader and one Bodyguard;
  `official_2` → 1 group of 2).

Expected fixture metadata:

| | official_1 | official_2 |
|---|---|---|
| `name` | `11th stuff` | `Awoo` |
| `points` | 2000 | 1260 |
| `super_faction` | `""` | `Space Marines` |
| `faction` | `T'au Empire` | `Space Wolves` |
| `detachments` | `["Retaliation Cadre"]` | `["Champions of Fenris", "Legends of Saga and Song", "Veterans of the Fang"]` |
| `detachment_points` | 3 | 3 |
| `disposition` | `Purge the Foe` | `Disruption` |
| `army_size` | `Strike Force` | `Strike Force` |
| `army_size_points` | 2000 | 2000 |
| unit count | 18 | 9 |

Unit-level tests name the example file each case came from, keeping the
existing convention.

## Removals and other changes

Removed:

- `src/listgrok/parsers/official_app.py` (superseded by the package)
- `src/tests/test_official_app.py` (rewritten)
- From `helpers.py`: `POINTS_LABEL_REGEX`, `NUM_REGEX`, `UNIT_TYPES`,
  `ParserStage`, `count_leading_hashes` — all dead once 10th ed goes. Only
  `count_leading_spaces` remains, used by `new_recruit_gw.py`.

Updated:

- `CLAUDE.md` Architecture section, which currently documents 10th ed dialects
  and `build_tree`.
- `pyproject.toml`'s description, which says "10th edition".
- `parse_list.py` import and fallback chain.
- `new_recruit_gw.py` and its tests, which follow the `detachment` →
  `detachments` rename. `_handle_header` writes the field with
  `setattr(army_list, "detachment", ...)`; because `ArmyList` is a plain
  dataclass with no `__slots__`, that call would keep succeeding after the
  rename, quietly writing a stray instance attribute that `to_json()` drops
  while `test_new_recruit.py`'s assertions keep reading it and passing. The
  rename must be followed through by hand, and verified with
  `grep -rn --include='*.py' "\.detachment\b" src/` returning nothing.

Untouched: `parse_error.py`, `examples/examples.py`.

## Done means

`make test`, `make lint` and `make typecheck` all pass; both fixtures parse to
the metadata in the table above; syntax stays 3.10-compatible; the runtime
dependency list stays empty.
