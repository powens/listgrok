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
