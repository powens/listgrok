import re
from dataclasses import dataclass, field

from listgrok.army.army_list import ArmyList, Unit, UnitComposition
from listgrok.parsers.helpers import (
    NUM_REGEX,
    POINTS_LABEL_REGEX,
    UNIT_TYPES,
    ParserStage,
    count_leading_spaces,
)
from listgrok.parsers.parse_error import ParseError

BULLET_REGEX = re.compile(r"^[•◦]\s+")
# An army-size line ends with a points label; the count may carry thousands commas.
ARMY_SIZE_REGEX = re.compile(r".+\(\d[\d,]*\s[Pp]oints\)$")


@dataclass
class Node:
    text: str
    indent: int
    children: list["Node"] = field(default_factory=list)


def _strip_bullet(line: str) -> tuple[str, bool]:
    if (match := BULLET_REGEX.match(line)) is not None:
        return line[match.end() :], True
    return line, False


def build_tree(body_lines: list[str]) -> list[Node]:
    """Build the indentation forest for a unit block's body (header excluded).

    Bullet glyphs vary between export dialects, so indentation is authoritative.
    A bulletless line is a continuation: it inherits the level of the most
    recent bulleted line, making it a sibling of that bullet rather than a child.
    """
    roots: list[Node] = []
    stack: list[Node] = []
    last_bulleted_indent: int | None = None

    for raw in body_lines:
        text, had_bullet = _strip_bullet(raw.strip())

        if had_bullet:
            indent = count_leading_spaces(raw)
            last_bulleted_indent = indent
        elif last_bulleted_indent is not None:
            indent = last_bulleted_indent
        else:
            indent = count_leading_spaces(raw)

        node = Node(text=text, indent=indent)

        while stack and stack[-1].indent >= indent:
            stack.pop()
        (stack[-1].children if stack else roots).append(node)
        stack.append(node)

    return roots


def _parse_header(line: str, unit_type: str) -> Unit:
    if (match := POINTS_LABEL_REGEX.match(line)) is None:
        raise ParseError("Unexpected unit header", line)
    unit = Unit()
    unit.name = match.group("name")
    unit.points = int(match.group("points"))
    unit.sheet_type = unit_type
    return unit


def _composition_from(text: str) -> UnitComposition:
    uc = UnitComposition()
    if (match := NUM_REGEX.match(text)) is not None:
        uc.num_models = int(match.group("num"))
        uc.name = match.group("name")
    else:
        uc.name = text
    return uc


def _apply_wargear(unit: Unit, uc: UnitComposition, text: str) -> None:
    if (match := NUM_REGEX.match(text)) is not None:
        uc.add_wargear(match.group("name"), int(match.group("num")))
    else:
        unit.decorations.append(text)


def _populate_unit(unit: Unit, roots: list[Node]) -> None:
    models: list[Node] = []
    for node in roots:
        if node.text == "Warlord":
            unit.is_warlord = True
        elif node.text.startswith(("Enhancement:", "Enhancements:")):
            unit.enhancement = node.text.split(":", 1)[1].strip()
        else:
            models.append(node)

    # A multi-model unit has model nodes with wargear nested beneath them.
    # A single-model unit has all wargear flat under one implicit model.
    if any(node.children for node in models):
        for node in models:
            uc = _composition_from(node.text)
            unit.add_model_set(uc)
            for child in node.children:
                _apply_wargear(unit, uc, child.text)
    else:
        uc = UnitComposition()
        uc.name = unit.name
        uc.num_models = 1
        unit.add_model_set(uc)
        for node in models:
            _apply_wargear(unit, uc, node.text)


def parse_unit_block(lines: list[str], unit_type: str, army_list: ArmyList) -> None:
    if len(lines) == 0:
        raise ParseError("Empty unit block", lines)

    unit = _parse_header(lines[0], unit_type)
    army_list.add_unit(unit)
    _populate_unit(unit, build_tree(lines[1:]))


def _parse_faction_block(collection: list[str], army_list: ArmyList) -> None:
    """Assign faction fields. The army-size line is found by pattern rather than
    position, since dialects place it either last or in the middle of the block.
    """
    size_lines = [line for line in collection if ARMY_SIZE_REGEX.match(line)]
    if len(size_lines) != 1:
        raise ParseError(
            f"Expected exactly one army-size line, found {len(size_lines)}",
            collection,
        )

    army_list.army_size = size_lines[0]
    rest = [line for line in collection if line != size_lines[0]]

    if len(rest) == 3:
        army_list.super_faction = rest[0]
        army_list.faction = rest[1]
        army_list.detachment = rest[2]
    elif len(rest) == 2:
        army_list.faction = rest[0]
        army_list.detachment = rest[1]
    else:
        raise ParseError(
            f"Expected 2 or 3 faction lines, found {len(rest)}", collection
        )


def _handle_start(collection: list[str], army_list: ArmyList) -> bool:
    """Parse the army-name block, returning True on success.

    Some exports omit the army name entirely and lead with the faction block.
    In that case the collection has no points label; return False and leave
    army_list untouched so the caller can treat it as the faction block.
    POINTS_LABEL_REGEX is re.DOTALL because some army names span multiple lines.
    """
    line = "\n".join(collection).strip()
    if (match := POINTS_LABEL_REGEX.match(line)) is None:
        return False
    army_list.name = match.group("name")
    army_list.points = int(match.group("points"))
    return True


def parse_official_app_v2(list_text: str) -> ArmyList:
    army_list = ArmyList()
    state = ParserStage.START
    unit_type = ""
    collection: list[str] = []

    for line in list_text.split("\n"):
        if not line.strip():
            if collection:
                if state == ParserStage.START:
                    if _handle_start(collection, army_list):
                        state = ParserStage.FACTION
                    else:
                        # No army-name header; this is already the faction block.
                        _parse_faction_block(collection, army_list)
                        state = ParserStage.UNIT_DETAILS
                elif state == ParserStage.FACTION:
                    _parse_faction_block(collection, army_list)
                    state = ParserStage.UNIT_DETAILS
                else:
                    if unit_type == "":
                        raise ParseError("No unit type found", collection)
                    parse_unit_block(collection, unit_type, army_list)
                collection = []
            continue

        if line.startswith("Exported with App Version:"):
            continue

        if line in UNIT_TYPES:
            unit_type = line
            continue

        collection.append(line)

    return army_list
