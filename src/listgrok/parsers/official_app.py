from dataclasses import dataclass
import re
from listgrok.army.army_list import Unit, ArmyList, UnitComposition
from listgrok.parsers.parse_error import ParseError
from listgrok.parsers.helpers import count_leading_spaces
from enum import Enum, auto

POINTS_LABEL_REGEX = re.compile(r"^(?P<name>.+)\s\((?P<points>\d+)\s[Pp]oints\)$")
POINTS_LABEL_REGEX_DOTALL = re.compile(
    r"^(?P<name>.+)\s\((?P<points>\d+)\s[Pp]oints\)$", re.DOTALL
)
NUM_REGEX = re.compile(r"^(?P<num>\d+)x\s(?P<name>.*)$")
UNIT_TYPES = frozenset(
    {
        "CHARACTERS",
        "OTHER DATASHEETS",
        "ALLIED UNITS",
        "BATTLELINE",
        "DEDICATED TRANSPORTS",
    }
)
LEADING_SPACES_FOR_SINGLE_MODEL_UNIT = 2


def _is_army_size_line(line: str) -> bool:
    return POINTS_LABEL_REGEX.match(line) is not None


class ParserStateMachine(Enum):
    START = auto()
    FACTION = auto()
    UNIT_DETAILS = auto()


@dataclass
class ParserState:
    state: ParserStateMachine
    line_collection: list[str]
    most_recent_unit_type: str
    list: ArmyList


def _handle_faction_collection(collection: list[str], army_list: ArmyList):
    line_count = len(collection)
    if line_count < 3 or line_count > 4:
        raise ParseError(f"line_count is {line_count}. Expected [3,4]", collection)

    army_list.army_size = collection[-1]
    army_list.detachment = collection[-2]

    if line_count == 4:
        army_list.super_faction = collection[0]
        army_list.faction = collection[1]
    else:
        army_list.faction = collection[0]


def _handle_unit_line(line: str, unit: Unit, uc: UnitComposition):
    line = line.strip()
    line = re.sub(r"^[•◦]\s", "", line)

    if line == "Warlord":
        unit.is_warlord = True
    elif line.startswith("Enhancements: "):
        unit.enhancement = line.removeprefix("Enhancements: ")
    else:
        if (match := re.match(NUM_REGEX, line)) is None:
            unit.decorations.append(line)
        else:
            uc.add_wargear(match.group("name"), int(match.group("num")))


def _parse_unit_header(line: str, unit_type: str) -> Unit:
    if (match := re.match(POINTS_LABEL_REGEX, line)) is None:
        raise ParseError("Unexpected unit_start", line)
    unit = Unit()
    unit.name = match.group("name")
    unit.points = int(match.group("points"))
    unit.sheet_type = unit_type
    return unit


def _populate_single_model_unit(lines: list[str], unit: Unit):
    uc = UnitComposition()
    uc.name = unit.name
    uc.num_models = 1
    unit.add_model_set(uc)
    for line in lines:
        _handle_unit_line(line, unit, uc)


def _populate_multi_model_unit(lines: list[str], unit: Unit):
    uc = None
    for line in lines:
        line = line.strip()
        if line.startswith("• "):
            line = line.removeprefix("• ")
            uc = UnitComposition()
            if (match := re.match(NUM_REGEX, line)) is not None:
                uc.num_models = int(match.group("num"))
                uc.name = match.group("name")
                unit.add_model_set(uc)
        elif line.startswith("◦ "):
            if uc is None:
                raise ParseError(
                    "Tried to add wargear to non-existent UnitComposition", line
                )
            _handle_unit_line(line, unit, uc)


def _handle_unit_block(lines: list[str], unit_type: str, army_list: ArmyList):
    if len(lines) == 0:
        raise ParseError("Empty unit block", lines)

    unit = _parse_unit_header(lines[0], unit_type)
    army_list.add_unit(unit)

    most_leading_spaces = max(count_leading_spaces(line) for line in lines)
    if most_leading_spaces == LEADING_SPACES_FOR_SINGLE_MODEL_UNIT:
        _populate_single_model_unit(lines[1:], unit)
    else:
        _populate_multi_model_unit(lines[1:], unit)


def parse_official_app(list_text: str) -> ArmyList:
    state = ParserState(
        state=ParserStateMachine.START,
        line_collection=[],
        most_recent_unit_type="",
        list=ArmyList(),
    )

    for line in list_text.split("\n"):
        if not line.strip():
            # We've reached the end of a chunk of list. Handle it
            if len(state.line_collection) > 0:
                match state.state:
                    case ParserStateMachine.START:
                        _handle_start(state)
                    case ParserStateMachine.FACTION:
                        _handle_faction(state)
                    case ParserStateMachine.UNIT_DETAILS:
                        _handle_unit_details(state)
                state.line_collection.clear()
            continue

        if line.startswith("Exported with App Version:"):
            continue

        if line in UNIT_TYPES:
            state.most_recent_unit_type = line
            continue

        state.line_collection.append(line)

    return state.list


def _handle_start(state: ParserState):
    line = "\n".join(state.line_collection).strip()
    # Need re.DOTALL here because some army lists have newlines in them, for some reason
    if (match := re.match(POINTS_LABEL_REGEX_DOTALL, line)) is None:
        raise ParseError("Expected army name", line)
    state.list.name = match.group("name")
    state.list.points = int(match.group("points"))
    state.state = ParserStateMachine.FACTION


def _handle_faction(state: ParserState):
    # We need to handle both factions with and without a super faction
    _handle_faction_collection(state.line_collection, state.list)
    state.state = ParserStateMachine.UNIT_DETAILS


def _handle_unit_details(state: ParserState):
    if state.most_recent_unit_type == "":
        raise ParseError("No unit type found", state.line_collection)

    _handle_unit_block(state.line_collection, state.most_recent_unit_type, state.list)


# def _parse_multi_model(lines: list[str], unit: Unit):
#     """Bullets are models, indented lines are wargear for that model."""
#     current_uc: UnitComposition | None = None

#     for line in lines:
#         stripped = line.strip().removeprefix("• ")

#         if line.strip().startswith("•"):
#             # New model
#             current_uc = UnitComposition()
#             if match := re.match(NUM_REGEX, stripped):
#                 current_uc.num_models = int(match.group("num"))
#                 current_uc.name = match.group("name")
#             unit.add_model_set(current_uc)
#         else:
#             # Wargear for current model
#             if current_uc and (match := re.match(NUM_REGEX, stripped)):
#                 current_uc.add_wargear(match.group("name"), int(match.group("num")))


# def _parse_single_model(lines: list[str], unit: Unit):
#     """Bullets and indented lines are all wargear for a single model."""
#     uc = UnitComposition()
#     uc.name = unit.name
#     uc.num_models = 1
#     unit.add_model_set(uc)

#     for line in lines:
#         stripped = line.strip().removeprefix("• ")
#         if match := re.match(NUM_REGEX, stripped):
#             uc.add_wargear(match.group("name"), int(match.group("num")))


# def _parse_unit_block(lines: list[str], unit_type: str, army_list: ArmyList):
#     unit = Unit()

#     # Parse Header: "Unit Name (65 Points)"
#     first_line = lines[0]
#     if (match := re.match(POINTS_LABEL_REGEX, first_line)) is None:
#         raise ParseError("Unexpected unit_start", first_line)
#     unit.name = match.group("name")
#     unit.points = int(match.group("points"))

#     # Detect format by checking indentation levels
#     # Multi-model: bullets at level 1, wargear indented further
#     # Single-model: wargear at level 1, all at same indent level

#     bullet_lines = [l for l in lines[1:] if l.strip().startswith("•")]
#     indented_lines = [
#         l for l in lines[1:] if not l.strip().startswith("•") and l.strip()
#     ]

#     # If we have indented lines after bullets → multi-model format
#     is_multi_model = (
#         any(
#             count_leading_spaces(l) > count_leading_spaces(bullet_lines[0])
#             for l in indented_lines
#         )
#         if bullet_lines and indented_lines
#         else False
#     )

#     if is_multi_model:
#         _parse_multi_model(lines[1:], unit)
#     else:
#         _parse_single_model(lines[1:], unit)

#     return unit
