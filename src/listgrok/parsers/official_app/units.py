"""Parse a unit block of an 11th edition official-app export.

The body comes in three dialects, chosen by build_tree:

- classic: indented. Bullets are stripped and the column the text starts at
  decides nesting (_indent_tree).
- glyph: a classic body that lost its indentation but bullets every line, so
  "•" versus "◦" decides nesting (_glyph_tree).
- compact: unindented, nesting encoded by bullet runs (_run_tree).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from listgrok.exceptions import ParseError
from listgrok.models import Attachment, Unit, UnitComposition
from listgrok.parsers.official_app.blocks import (
    ATTACHED_AS_REGEX,
    BULLET_REGEX,
    NUM_REGEX,
    POINTS_REGEX,
    parse_points,
)

HOLLOW_BULLET = "◦"
# English, French and German. French puts a space before the colon.
WARLORD_LINES = frozenset({"Warlord", "Seigneur de Guerre", "Kriegsherr"})
ENHANCEMENT_REGEX = re.compile(
    r"^(?:Enhancements?|Optimisations?|Verbesserung(?:en)?)\s?:\s*(?P<name>.*)$"
)
# Attached-as roles and details are a closed set, so the French and German
# words map to the English ones and a consumer filtering on "Leader" needs no
# translation table. A word not listed is kept verbatim.
ROLE_NAMES = {
    "Meneur": "Leader",
    "Appui": "Support",
    "Gardes du Corps": "Bodyguard",
    "Anführer": "Leader",
    "Unterstützung": "Support",
    "Leibwächter": "Bodyguard",
}
ROLE_DETAILS = {
    "Personnage": "Character",
    "Ligne": "Battleline",
    "Charaktermodell": "Character",
    "Linientruppen": "Battleline",
}


@dataclass
class Node:
    text: str
    indent: int
    children: list["Node"] = field(default_factory=list)


def build_tree(body_lines: Sequence[str]) -> list[Node]:
    """Build the forest for a unit block's body (header excluded)."""
    if any(len(raw) - len(raw.lstrip()) for raw in body_lines):
        return _indent_tree(body_lines)
    if all(BULLET_REGEX.match(raw) for raw in body_lines):
        return _glyph_tree(body_lines)
    return _run_tree(body_lines)


def _indent_tree(body_lines: Sequence[str]) -> list[Node]:
    roots: list[Node] = []
    stack: list[Node] = []

    for raw in body_lines:
        text = BULLET_REGEX.sub("", raw.strip())
        # Nesting is measured at the text, not the bullet: the v2.6.0 (144)
        # export continues a bulleted list with unbulleted lines aligned under
        # the first one's text ("  • 1x Baleflamer" / "    1x Combi-bolter"),
        # and those are siblings, not children.
        indent = len(raw.rstrip()) - len(text)
        node = Node(text=text, indent=indent)

        while stack and stack[-1].indent >= indent:
            stack.pop()
        (stack[-1].children if stack else roots).append(node)
        # The same export puts "• Attached as: …" one level out from the rest
        # of the body; it is a keyword line and never holds children.
        if not ATTACHED_AS_REGEX.match(text):
            stack.append(node)

    return roots


def _glyph_tree(body_lines: Sequence[str]) -> list[Node]:
    """Build the forest for an unindented body where every line is bulleted.

    A "◦" line is wargear of the nearest "•" line above it that is not a
    keyword; every "•" line is a root. A body with no "◦" line therefore stays
    flat, like a single-model unit in the classic dialect. Skipping keywords
    matters because the indented export nests "Warlord" under the model that
    carries it, above that model's wargear (official_11); with the indentation
    gone it reads "• 1x Tempestor Prime" / "• Warlord" / "◦ 1x Command Rod",
    and the Command Rod belongs to the Tempestor Prime.
    """
    roots: list[Node] = []
    parent: Node | None = None
    for raw in body_lines:
        node = Node(text=BULLET_REGEX.sub("", raw), indent=0)
        if raw.startswith(HOLLOW_BULLET) and parent is not None:
            parent.children.append(node)
            continue
        roots.append(node)
        if not _is_keyword(node.text):
            parent = node
    return roots


def _run_tree(body_lines: Sequence[str]) -> list[Node]:
    """Build the forest for the newer dialect's unindented bullet-run body.

    A bulleted line followed by another bulleted line is a root. Everything
    else is a run member: a bulleted line starting a plain run, or a plain
    line continuing one. A run holds the wargear of the root above it — but
    only when that root is "Nx"-shaped; after a keyword root ("Warlord",
    "Attached as: …") the run stays at the top level, which is also where
    single-model bodies and Wartrakk-style bare wargear names end up, exactly
    mirroring the classic dialect's flat body.
    """
    lines = [line.strip() for line in body_lines]
    bulleted = [BULLET_REGEX.match(line) is not None for line in lines]
    roots: list[Node] = []
    parent: Node | None = None

    for i, line in enumerate(lines):
        node = Node(text=BULLET_REGEX.sub("", line), indent=0)
        if bulleted[i] and i + 1 < len(lines) and bulleted[i + 1]:
            roots.append(node)
            parent = node if NUM_REGEX.match(node.text) else None
        elif parent is not None:
            parent.children.append(node)
        else:
            roots.append(node)

    return roots


def parse_unit(lines: Sequence[str], sheet_type: str) -> Unit:
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


def _is_keyword(text: str) -> bool:
    """True for a unit-level keyword line that _lift_keyword would apply."""
    return (
        text in WARLORD_LINES
        or ENHANCEMENT_REGEX.match(text) is not None
        or ATTACHED_AS_REGEX.match(text) is not None
    )


def _lift_keyword(unit: Unit, text: str) -> bool:
    """Apply a unit-level keyword line to `unit`; False if `text` is not one."""
    if text in WARLORD_LINES:
        unit.is_warlord = True
    elif (match := ENHANCEMENT_REGEX.match(text)) is not None:
        unit.enhancement = match.group("name").strip()
    elif (match := ATTACHED_AS_REGEX.match(text)) is not None:
        role = match.group("role").strip()
        # The newer dialect may omit the parenthetical entirely.
        detail = (match.group("detail") or "").strip()
        unit.attachment = Attachment(
            role=ROLE_NAMES.get(role, role),
            role_detail=_translate_role_detail(detail),
        )
    else:
        return False
    return True


def _translate_role_detail(detail: str) -> str:
    """Map each keyword of an attached-as detail ("Personnage, Ligne") to English."""
    return ", ".join(
        ROLE_DETAILS.get(keyword.strip(), keyword.strip())
        for keyword in detail.split(",")
    )


def _populate(unit: Unit, roots: list[Node]) -> None:
    models = [node for node in roots if not _lift_keyword(unit, node.text)]

    # Nested children mean each root is a model set with its wargear beneath.
    # A flat body means one implicit model set holding all of the wargear.
    if any(node.children for node in models):
        for node in models:
            match = NUM_REGEX.match(node.text)
            if match is None:
                # Not a model set we can count; like _add_wargear, keep it as
                # a decoration rather than invent num_models.
                unit.decorations.append(node.text)
                continue
            model_set = UnitComposition(
                name=match.group("name"), num_models=int(match.group("num"))
            )
            unit.add_model_set(model_set)
            # Only one level is read: a third level (none in any fixture)
            # would be dropped silently.
            for child in node.children:
                # In a multi-model unit the app writes "Warlord" and the
                # enhancement under the model that carries it (official_11,
                # official_25), so the keyword lift applies here too.
                if not _lift_keyword(unit, child.text):
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
