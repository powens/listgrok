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
            match = NUM_REGEX.match(node.text)
            if match is None:
                # Mirrors _add_wargear: a root that isn't "Nx name" is not a
                # model set we can name or count, so it goes to decorations
                # rather than fabricating a UnitComposition with num_models=None.
                unit.decorations.append(node.text)
                continue
            model_set = UnitComposition(
                name=match.group("name"), num_models=int(match.group("num"))
            )
            unit.add_model_set(model_set)
            # NOTE: only one level of nesting is visited here (child.text, not
            # child.children). No 11th ed fixture nests a third level, but if
            # one ever does, it would be silently dropped rather than raising.
            for child in node.children:
                _add_wargear(unit, model_set, child.text)
    else:
        model_set = UnitComposition(name=unit.name, num_models=1)
        unit.add_model_set(model_set)
        for node in models:
            _add_wargear(unit, model_set, node.text)


def _add_wargear(unit: Unit, model_set: UnitComposition, text: str) -> None:
    if (match := NUM_REGEX.match(text)) is not None:
        model_set.add_wargear(match.group("name"), int(match.group("num")))
    else:
        unit.decorations.append(text)
