"""Split a GW official-app (11th edition) export into classified blocks.

Classification is by shape alone — no army-list knowledge lives here. The
metadata block is identified by its "(N Detachment Points)" line, which no other
block carries; everything before it is the army name, everything after it is
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
GROUP_REGEX = re.compile(r"^Attached unit\b")
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
        # An excerpt, not the whole document: ParseError.__str__ renders the
        # block after "on line", and the full text would make that unreadable.
        first_line = text.split("\n", 1)[0]
        raise ParseError("No header block found", first_line)
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
        if _is_section_heading(line):
            return BlockKind.SECTION
        if GROUP_REGEX.match(line):
            return BlockKind.GROUP
        raise ParseError("Unrecognised lone line", lines)

    raise ParseError("Unrecognised block", lines)


def _is_section_heading(line: str) -> bool:
    """A section heading shouts: "ATTACHED UNITS", not "Attached unit 1"."""
    return any(char.isalpha() for char in line) and line == line.upper()
