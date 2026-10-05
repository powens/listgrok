"""Split a GW official-app (11th edition) export into classified blocks.

Classification is by shape alone — no army-list knowledge lives here. The
metadata block is identified by its "(N Detachment Points)" line, which no other
block carries; before it is free text (the army name, up to its "(N Points)"
line, and any notes the player added, which are dropped), after it come
section headings, attachment-group headings and unit blocks. Keying off that
line rather than off "the points line is not first" is what lets a multi-line
army name work: under the latter rule it has exactly the header's shape.

This module is also the shared home for the export's regex patterns —
including NUM_REGEX, ATTACHED_AS_REGEX and BULLET_REGEX, which this module
does not itself use. They live here so units.py has one place to import them
from alongside POINTS_REGEX and DETACHMENT_REGEX, which classification does use.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto

from listgrok.exceptions import ParseError

# re.DOTALL so a multi-line army name matches as a single name. Point totals may
# carry thousands commas ("2,000 Points"), and \s+ keeps a doubled space before
# the parenthetical ("I choose violence.  (2,000 Points)") off the name.
POINTS_REGEX = re.compile(
    r"^(?P<name>.+?)\s+\((?P<points>[\d,]+)\s[Pp]oints\)$", re.DOTALL
)
DETACHMENT_REGEX = re.compile(
    r"^(?P<name>.+?)\s\((?P<points>\d+)\sDetachment\s[Pp]oints?\)$"
)
NUM_REGEX = re.compile(r"^(?P<num>\d+)x\s(?P<name>.+)$")
ATTACHED_AS_REGEX = re.compile(
    r"^Attached as:\s*(?P<role>[^(]+?)\s*(?:\((?P<detail>[^)]*)\))?$"
)
BULLET_REGEX = re.compile(r"^[•◦]\s*")
# IGNORECASE: the classic dialect writes "Attached unit 1", the newer one
# "Attached Unit 1". The \b keeps the plural section heading ("Attached
# Units") from matching.
GROUP_REGEX = re.compile(r"^Attached unit\b", re.IGNORECASE)
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
    lines: tuple[str, ...]


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
    raw_blocks = split_blocks(text)
    header_at = next(
        (i for i, lines in enumerate(raw_blocks) if _is_header(lines)), None
    )
    if header_at is None:
        # An excerpt, not the whole document: ParseError.__str__ renders the
        # block after "in block", and the full text would make that unreadable.
        first_line = text.split("\n", 1)[0]
        raise ParseError("No header block found", first_line)

    blocks: list[Block] = []
    name_lines = _army_name_lines(raw_blocks[:header_at])
    if name_lines:
        blocks.append(Block(kind=BlockKind.ARMY_NAME, lines=tuple(name_lines)))
    for lines in raw_blocks[header_at:]:
        blocks += _classify_block(lines)
    return blocks


def _army_name_lines(blocks: list[list[str]]) -> list[str]:
    """Return the army name: everything up to the first "(N Points)" line.

    The text above the header is free-form. An army name may itself contain
    blank lines ("Round 2 list", blank, "QFP (2,000 Points)"), so the blank
    separators are kept and the name reads back verbatim. Anything after the
    name's points line is the player's notes and is dropped, as is everything
    when no line carries a points suffix (the compact dialect has no name).
    """
    lines = [line for block in blocks for line in (*block, "")]
    for i, line in enumerate(lines):
        if POINTS_REGEX.match(line.strip()):
            return lines[: i + 1]
    return []


def _classify_block(lines: list[str]) -> list[Block]:
    """Classify one physical block, splitting a fused section+group pair."""
    if _is_fused_section_group(lines):
        return [
            Block(kind=BlockKind.SECTION, lines=(lines[0],)),
            Block(kind=BlockKind.GROUP, lines=(lines[1],)),
        ]
    return [Block(kind=_classify(lines), lines=tuple(lines))]


def _is_fused_section_group(lines: list[str]) -> bool:
    """The newer dialect writes no blank line between the attached-units
    heading and the first group heading ("Attached Units" / "Attached Unit 1").
    The group line is the marker; the single line above it is a section heading
    (title-case here, so the ALL-CAPS rule cannot spot it on its own).
    """
    if len(lines) != 2:
        return False
    heading, group = (line.strip() for line in lines)
    return (
        GROUP_REGEX.match(group) is not None
        and GROUP_REGEX.match(heading) is None
        and POINTS_REGEX.match(heading) is None
        and any(char.isalpha() for char in heading)
    )


def _classify(lines: list[str]) -> BlockKind:
    if lines[0].startswith(TRAILER_PREFIX):
        return BlockKind.TRAILER

    if _is_header(lines):
        return BlockKind.HEADER

    if POINTS_REGEX.match(lines[0].strip()):
        return BlockKind.UNIT

    if len(lines) == 1:
        line = lines[0].strip()
        if _is_section_heading(line):
            return BlockKind.SECTION
        if GROUP_REGEX.match(line):
            return BlockKind.GROUP
        raise ParseError("Unrecognised lone line", lines)

    raise ParseError("Unrecognised block", lines)


def _is_header(lines: list[str]) -> bool:
    return any(DETACHMENT_REGEX.match(line.strip()) for line in lines)


def _is_section_heading(line: str) -> bool:
    """A section heading shouts: "ATTACHED UNITS", not "Attached unit 1"."""
    return any(char.isalpha() for char in line) and line == line.upper()
