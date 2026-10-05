"""Parse a unit block of an 11th edition official-app export.

The body comes in three dialects. The classic export indents: bullet glyphs
are stripped and the column the text starts at decides nesting, so a body line
indented deeper than the line above it is that line's child. The newer compact
export writes every line at column zero and encodes nesting with bullet runs
instead — see _run_tree. Some v2.6.0 (3) exports also write every line at
column zero but nest wargear under a "◦" sub-bullet — see _sub_bullet_tree.
That last dialect is told apart per list, not per unit: a single-model unit in
it has no "◦" line and would otherwise read as a bullet run.
"""

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

WARLORD_LINE = "Warlord"
ENHANCEMENT_PREFIXES = ("Enhancements:", "Enhancement:")
SUB_BULLET = "◦"


@dataclass
class Node:
    text: str
    indent: int
    children: list["Node"] = field(default_factory=list)


def build_tree(body_lines: Sequence[str], sub_bullets: bool = False) -> list[Node]:
    """Build the forest for a unit block's body (header excluded).

    sub_bullets says the export nests wargear under column-zero "◦" lines.
    """
    if any(len(raw) - len(raw.lstrip()) for raw in body_lines):
        return _indent_tree(body_lines)
    if sub_bullets:
        return _sub_bullet_tree(body_lines)
    return _run_tree(body_lines)


def has_sub_bullets(text: str) -> bool:
    """Whether an export uses the column-zero "◦" sub-bullet dialect."""
    return any(line.startswith(SUB_BULLET) for line in text.split("\n"))


def _sub_bullet_tree(body_lines: Sequence[str]) -> list[Node]:
    roots: list[Node] = []
    # A keyword line can sit between a model and its "◦" wargear
    # (official_11's "• Warlord"), so sub-bullets go to the last model line.
    model: Node | None = None
    for raw in body_lines:
        line = raw.strip()
        node = Node(text=BULLET_REGEX.sub("", line), indent=0)
        if line.startswith(SUB_BULLET) and model is not None:
            model.children.append(node)
        else:
            roots.append(node)
            if not _is_keyword(node.text):
                model = node
    return roots


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
        # A keyword line is never wargear, even when it ends the body right
        # after a run (official_16's Gretchin close on "• Enhancement: …").
        if _is_keyword(node.text) or (
            bulleted[i] and i + 1 < len(lines) and bulleted[i + 1]
        ):
            roots.append(node)
            parent = node if NUM_REGEX.match(node.text) else None
        elif parent is not None:
            parent.children.append(node)
        else:
            roots.append(node)

    return roots


def parse_unit(
    lines: Sequence[str], sheet_type: str, sub_bullets: bool = False
) -> Unit:
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
    _populate(unit, build_tree(lines[1:], sub_bullets))
    return unit


def _populate(unit: Unit, roots: list[Node]) -> None:
    models = [node for node in roots if not _lift_keyword(unit, node.text)]

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
                # The sub-bullet dialect files an enhancement under the model
                # that carries it ("◦ Enhancements: Recon Hunter").
                if not _lift_keyword(unit, child.text):
                    _add_wargear(unit, model_set, child.text)
    else:
        model_set = UnitComposition(name=unit.name, num_models=1)
        unit.add_model_set(model_set)
        for node in models:
            _add_wargear(unit, model_set, node.text)


def _is_keyword(text: str) -> bool:
    return (
        text == WARLORD_LINE
        or text.startswith(ENHANCEMENT_PREFIXES)
        or ATTACHED_AS_REGEX.match(text) is not None
    )


def _lift_keyword(unit: Unit, text: str) -> bool:
    """Apply a keyword line to the unit; False if the line is not one."""
    if text == WARLORD_LINE:
        unit.is_warlord = True
    elif text.startswith(ENHANCEMENT_PREFIXES):
        unit.enhancement = text.split(":", 1)[1].strip()
    elif (match := ATTACHED_AS_REGEX.match(text)) is not None:
        unit.attachment = Attachment(
            role=match.group("role").strip(),
            # The newer dialect may omit the parenthetical entirely.
            role_detail=(match.group("detail") or "").strip(),
        )
    else:
        return False
    return True


def _add_wargear(unit: Unit, model_set: UnitComposition, text: str) -> None:
    if (match := NUM_REGEX.match(text)) is not None:
        model_set.add_wargear(match.group("name"), int(match.group("num")))
    else:
        unit.decorations.append(text)
