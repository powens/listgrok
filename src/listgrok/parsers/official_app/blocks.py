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

# The patterns below run on untrusted text, so they avoid two hazards. Adjacent
# quantifiers that can both match whitespace backtrack quadratically on a long
# whitespace run, so a name or role always ends in a non-space character.
# Unbounded digit runs reach int(), which raises ValueError past 4300 digits,
# so counts are capped and an oversized one simply fails to match.

# re.DOTALL so a multi-line army name matches as a single name. Point totals may
# carry thousands commas ("2,000 Points"), and \s+ keeps a doubled space before
# the parenthetical ("I choose violence.  (2,000 Points)") off the name.
POINTS_REGEX = re.compile(
    r"^(?P<name>.*?\S)\s+\((?P<points>[\d,]{1,9})\s[Pp]oints\)$", re.DOTALL
)
DETACHMENT_REGEX = re.compile(
    r"^(?P<name>.+?)\s\((?P<points>\d{1,6})\sDetachment\s[Pp]oints?\)$"
)
NUM_REGEX = re.compile(r"^(?P<num>\d{1,6})x\s(?P<name>.+)$")
ATTACHED_AS_REGEX = re.compile(
    r"^Attached as:\s*(?P<role>[^(\s](?:[^(]*[^(\s])?)\s*"
    r"(?:\((?P<detail>[^)]*)\))?$"
)
BULLET_REGEX = re.compile(r"^[•◦]\s*")
# IGNORECASE: the classic dialect writes "Attached unit 1", the newer one
# "Attached Unit 1". The \b keeps the plural section heading ("Attached
# Units") from matching.
GROUP_REGEX = re.compile(r"^Attached unit\b", re.IGNORECASE)
# Some exports underline each group heading ("Attached unit 1" / "======",
# official_31). Only that position is decoration; a rule elsewhere still raises.
UNDERLINE_REGEX = re.compile(r"^=+$")
# The official app's footer is known by its prefix, "Exported with App Version: …";
# another exporter's by naming a data version too, "Exported with New Recruit v37.14,
# Data Version: v8". Bounded, as the text is untrusted.
TRAILER_REGEX = re.compile(r"^Exported with (?:App Version:|.{1,80}Data Version:)")
# A header line that means to be the army size but is not POINTS_REGEX's shape:
# the size line is optional, so this one would otherwise map as a faction line.
# Leading \b and a capped run: a long digit or comma run cannot restart the scan.
LOOSE_POINTS_REGEX = re.compile(r"\b\d[\d,]{0,8}\s?(?:pts?|points?)\b", re.IGNORECASE)


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
    for line in text.replace("\r\n", "\n").split("\n"):
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
    name_lines: list[str] = []
    for lines in split_blocks(text):
        if not seen_header and not _is_header(lines):
            # Everything before the header is the army name: it may run over
            # several blocks ("Round 2 list", blank, "QFP (2,000 Points)") and
            # need not end in a points suffix (official_28). The blank
            # separators are kept so the name reads back verbatim.
            name_lines += [""] if name_lines else []
            name_lines += lines
            continue
        if name_lines:
            blocks.append(Block(kind=BlockKind.ARMY_NAME, lines=tuple(name_lines)))
            name_lines = []
        for block in _classify_block(lines, seen_header):
            seen_header = seen_header or block.kind is BlockKind.HEADER
            blocks.append(block)

    if not seen_header:
        # An excerpt, not the whole document: ParseError.__str__ renders the
        # block after "in block", and the full text would make that unreadable.
        first_line = text.split("\n", 1)[0]
        raise ParseError("No header block found", first_line)
    return blocks


def _classify_block(lines: list[str], seen_header: bool) -> list[Block]:
    """Classify one physical block, first splitting it where it fused several."""
    if not seen_header or _is_header(lines):
        head, tail = _split_header_tail(lines)
        header = Block(kind=_classify(head), lines=tuple(head))
        return [header, *(_classify_block(tail, True) if tail else [])]
    if len(lines) >= 2 and _is_fused_section_group(lines[:2]):
        return [
            Block(kind=BlockKind.SECTION, lines=(lines[0],)),
            *_classify_block(lines[1:], seen_header),
        ]
    return [
        Block(kind=_classify(chunk), lines=tuple(chunk))
        for chunk in _split_fused(lines)
    ]


def _split_header_tail(lines: list[str]) -> tuple[list[str], list[str]]:
    """Cut a section or group heading, and all after it, off the header block:
    New Recruit can leave out the blank line after the header too. Only lines
    after the detachment line are looked at, and only headings split, since a
    unit header has the same shape as the army-size line.
    """
    detachment = next(
        (i for i, line in enumerate(lines) if DETACHMENT_REGEX.match(line.strip())),
        len(lines),
    )
    for index in range(detachment + 1, len(lines)):
        line = lines[index].strip()
        if _is_section_heading(line) or _is_group_heading(line):
            return lines[:index], lines[index:]
    return lines, []


def _split_fused(lines: list[str]) -> list[list[str]]:
    """Split a block wherever a line starts a new one: New Recruit can leave out
    the blank line after a group heading or between units.

    Margin is measured from the block's first line, so a uniformly indented
    block splits like any other. A group heading is always a lone line, so the
    line after one starts a new block whatever the body's indentation, unless
    it is the heading's underline, which is dropped.
    """
    margin = _indent(lines[0])
    nested = any(_indent(line) > margin for line in lines)
    chunks: list[list[str]] = []
    after_group = False
    for line in lines:
        if after_group and UNDERLINE_REGEX.match(line.strip()):
            continue
        if (
            not chunks
            or after_group
            or (_indent(line) <= margin and _starts_block(line, nested))
        ):
            chunks.append([line])
        else:
            if not nested and _looks_like_unit_header(line):
                raise ParseError(
                    "Unit header inside a compact body; expected a blank line "
                    "before it",
                    lines,
                )
            chunks[-1].append(line)
        after_group = chunks[-1] == [line] and _is_group_heading(line.strip())
    return chunks


def _starts_block(line: str, nested: bool) -> bool:
    """Does this line, at the block's margin, begin a block of its own?

    Group headings and footers are unmistakable. A "(N Points)" line or an
    ALL-CAPS line is only structural when the body is `nested`: a compact body
    writes its run lines at the margin too, and they can have either shape.
    """
    line = line.strip()
    if BULLET_REGEX.match(line):
        return False
    if _is_group_heading(line) or TRAILER_REGEX.match(line):
        return True
    return nested and (
        POINTS_REGEX.match(line) is not None or _is_section_heading(line)
    )


def _looks_like_unit_header(line: str) -> bool:
    """A compact body's run lines are "Nx" wargear, bare wargear names or
    "Keyword: …" lines, so an unbulleted "(N Points)" line that is none of
    those is a unit header with its blank line missing. It cannot be split off
    safely, but swallowing it would drop its points, so the parse fails.
    """
    line = line.strip()
    match = POINTS_REGEX.match(line)
    return (
        match is not None
        and BULLET_REGEX.match(line) is None
        and NUM_REGEX.match(line) is None
        and ":" not in match.group("name")
    )


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


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
        _is_group_heading(group)
        and GROUP_REGEX.match(heading) is None
        and POINTS_REGEX.match(heading) is None
        and any(char.isalpha() for char in heading)
    )


def _classify(lines: list[str]) -> BlockKind:
    """Classify the header block or a block after it.

    classify_blocks has already folded every block before the header into the
    army name, so only the header itself can arrive here with seen_header unset.
    """
    if TRAILER_REGEX.match(lines[0].strip()):
        return BlockKind.TRAILER

    if _is_header(lines):
        return BlockKind.HEADER

    if POINTS_REGEX.match(lines[0].strip()):
        return BlockKind.UNIT

    if len(lines) == 1:
        line = lines[0].strip()
        if _is_section_heading(line):
            return BlockKind.SECTION
        if _is_group_heading(line):
            return BlockKind.GROUP
        raise ParseError("Unrecognised lone line", lines)

    raise ParseError("Unrecognised block", lines)


def _is_header(lines: list[str]) -> bool:
    return any(DETACHMENT_REGEX.match(line.strip()) for line in lines)


def _is_group_heading(line: str) -> bool:
    """The "(N Points)" suffix outranks the prefix: that line is a unit header."""
    return GROUP_REGEX.match(line) is not None and POINTS_REGEX.match(line) is None


def _is_section_heading(line: str) -> bool:
    """A section heading shouts: "ATTACHED UNITS", not "Attached unit 1"."""
    return any(char.isalpha() for char in line) and line == line.upper()
