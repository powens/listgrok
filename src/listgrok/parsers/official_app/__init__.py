"""Parse army lists exported from GW's official Warhammer 40k app (11th edition).

The export is folded from a classified block stream into an ArmyList, carrying
only the current sheet type and the current attachment group as state.
"""

from collections.abc import Sequence

from listgrok.exceptions import ParseError
from listgrok.models import ArmyList, Attachment, Unit
from listgrok.parsers.official_app.blocks import (
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

    for block in classify_blocks(list_text):
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
            army_list.add_unit(_parse_unit_in(block.lines, sheet_type, group))
        elif block.kind is BlockKind.TRAILER:
            pass
        else:
            # classify_blocks only ever emits the BlockKind members handled
            # above; this guards against a future kind being added there and
            # silently falling through here instead of being wired in.
            raise ParseError(f"Unhandled block kind: {block.kind}", block.lines)

    return army_list


def _parse_army_name(lines: Sequence[str], army_list: ArmyList) -> None:
    match = POINTS_REGEX.match("\n".join(lines).strip())
    if match is None:
        # Unreachable in practice: classify_blocks only labels a block
        # ARMY_NAME after this exact regex already matched it. Kept as
        # defensive insurance against that invariant changing underfoot.
        raise ParseError("Unexpected army-name block", lines)
    army_list.name = match.group("name")
    army_list.points = parse_points(match.group("points"))


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
