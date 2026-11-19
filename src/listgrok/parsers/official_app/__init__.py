"""Parse army lists exported from GW's official Warhammer 40k app (11th edition),
and New Recruit's export of the same layout.

The export is folded from a classified block stream into an ArmyList, carrying
only the current sheet type, the current attachment group and the unit a
footnote may describe as state.
"""

from collections.abc import Sequence

from listgrok.exceptions import ParseError
from listgrok.models import ArmyList, Attachment, Unit
from listgrok.parsers.official_app.blocks import (
    BULLET_REGEX,
    POINTS_REGEX,
    BlockKind,
    classify_blocks,
    parse_points,
)
from listgrok.parsers.official_app.header import parse_header
from listgrok.parsers.official_app.units import parse_unit

__all__ = ["parse_official_app"]


def parse_official_app(list_text: str) -> ArmyList:
    army_list = ArmyList()
    sheet_type = ""
    group = ""
    seen_header = False
    # The unit just parsed, if its header ends in the "*" footnote marker.
    footnoted: Unit | None = None

    for block in classify_blocks(list_text):
        if block.kind is not BlockKind.FOOTNOTE:
            footnoted = None
        if block.kind is BlockKind.ARMY_NAME:
            _parse_army_name(block.lines, army_list)
        elif block.kind is BlockKind.HEADER:
            if seen_header:
                raise ParseError("Duplicate header block", block.lines)
            parse_header(block.lines, army_list)
            seen_header = True
        elif block.kind is BlockKind.SECTION:
            # Upper-cased so the newer dialect's title-case fused heading
            # ("Attached Units") reads the same as the classic "ATTACHED
            # UNITS"; classic headings are already all-caps.
            sheet_type = block.lines[0].strip().upper()
            group = ""
        elif block.kind is BlockKind.GROUP:
            group = block.lines[0].strip()
        elif block.kind is BlockKind.UNIT:
            unit = _parse_unit_in(block.lines, sheet_type, group)
            army_list.add_unit(unit)
            if block.lines[0].strip().endswith("*"):
                footnoted = unit
        elif block.kind is BlockKind.VALIDATION_ERRORS:
            army_list.validation_errors += [
                BULLET_REGEX.sub("", line.strip()) for line in block.lines[1:]
            ]
        elif block.kind is BlockKind.FOOTNOTE:
            # A footnote describes the "*"-marked unit directly above it, so
            # it joins that unit's decorations. The app prints no other kind,
            # so one anywhere else is malformed input.
            if footnoted is None:
                raise ParseError(
                    "Footnote not directly below a unit marked '*'", block.lines
                )
            footnoted.decorations += [
                line.strip().removeprefix("*").strip() for line in block.lines
            ]
        elif block.kind is BlockKind.TRAILER:
            pass
        else:
            # Guards a BlockKind added to classify_blocks but not wired in here.
            raise ParseError(f"Unhandled block kind: {block.kind}", block.lines)

    return army_list


def _parse_army_name(lines: Sequence[str], army_list: ArmyList) -> None:
    """Read the name and list points from the text before the header.

    The name runs up to the last line ending in "(N Points)", whose suffix is
    the list's points total; it may span blank lines ("Round 2 list", blank,
    "QFP (2,000 Points)"). Anything after that line is player notes and is
    dropped, best effort (lvo2026_chaos_space_marines, lvo2026_grey_knights).
    With no points line, the first block is the name, any later blocks are
    dropped, and points stays None (official_28).
    """
    for end in reversed(range(len(lines))):
        if (match := POINTS_REGEX.match(lines[end].strip())) is not None:
            army_list.name = "\n".join([*lines[:end], match.group("name")]).strip()
            army_list.points = parse_points(match.group("points"))
            return
    first_block = lines[: lines.index("")] if "" in lines else lines
    army_list.name = "\n".join(first_block).strip()


def _parse_unit_in(lines: Sequence[str], sheet_type: str, group: str) -> Unit:
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
