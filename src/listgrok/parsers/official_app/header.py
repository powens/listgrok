"""Parse the metadata block of an 11th edition official-app export.

The two labelled lines are found by pattern, not position, because the app has
moved them between dialects before. What remains maps by order.
"""

from collections.abc import Sequence

from listgrok.exceptions import ParseError
from listgrok.models import ArmyList
from listgrok.parsers.official_app.blocks import (
    DETACHMENT_REGEX,
    POINTS_REGEX,
    parse_points,
)

DISPOSITION_LABEL = "Force Dispositions:"


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


def parse_header(lines: Sequence[str], army_list: ArmyList) -> None:
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
    army_list.detachment_points = parse_points(detachment.group("points"))

    consumed = {size.group(0), detachment.group(0)}
    rest = [line for line in lines if line not in consumed]

    # The newer dialect labels the disposition line ("Force Dispositions: X"),
    # making it the third pattern-found line; the classic dialect leaves it
    # unlabelled and it maps by order below.
    labelled = [line for line in rest if line.startswith(DISPOSITION_LABEL)]
    if labelled:
        if len(labelled) > 1:
            raise ParseError("Expected at most one disposition line", lines)
        army_list.disposition = labelled[0].removeprefix(DISPOSITION_LABEL).strip()
        rest = [line for line in rest if line not in labelled]
        if len(rest) == 2:
            army_list.super_faction, army_list.faction = rest
        elif len(rest) == 1:
            army_list.faction = rest[0]
        else:
            raise ParseError(f"Expected 1 or 2 faction lines, found {len(rest)}", lines)
        return

    if len(rest) == 3:
        army_list.super_faction, army_list.faction, army_list.disposition = rest
    elif len(rest) == 2:
        army_list.faction, army_list.disposition = rest
    elif len(rest) == 1:
        army_list.faction = rest[0]
    else:
        raise ParseError(f"Expected 1 to 3 faction lines, found {len(rest)}", lines)
