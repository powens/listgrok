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
LEADING_SPACES_FOR_UNIT_COMPOSITION = 2


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


def _is_army_size_line(line: str) -> bool:
    return re.match(POINTS_LABEL_REGEX, line) is not None


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

    remove_prefixes = ["• ", "◦ "]
    for rp in remove_prefixes:
        if line.startswith(rp):
            line = line.removeprefix(rp)

    if line == "Warlord":
        unit.is_warlord = True
    elif line.startswith("Enhancements: "):
        unit.enhancement = line.removeprefix("Enhancements: ")
    else:
        if (match := re.match(NUM_REGEX, line)) is None:
            raise ParseError("Unexpected unit line", line)

        uc.add_wargear(match.group("name"), int(match.group("num")))


# TODO: Refactor this
def _handle_unit_block(lines: list[str], unit_type: str, list: ArmyList):
    # Determine if this is a single model or multiple model unit
    most_leading_spaces = max(count_leading_spaces(line) for line in lines)

    unit = Unit()

    first_line = lines[0]

    if (match := re.match(POINTS_LABEL_REGEX, first_line)) is None:
        raise ParseError("Unexpected unit_start", first_line)
    unit.name = match.group("name")
    unit.points = int(match.group("points"))
    unit.sheet_type = unit_type

    list.add_unit(unit)

    if most_leading_spaces == LEADING_SPACES_FOR_UNIT_COMPOSITION:
        uc = UnitComposition()
        uc.name = unit.name
        uc.num_models = 1
        unit.add_model_set(uc)
        for line in lines[1:]:
            _handle_unit_line(line, unit, uc)

    else:
        uc = None
        for line in lines:
            line = line.strip()
            if line.startswith("• "):
                line = line.removeprefix("• ")
                uc = UnitComposition()

                match = re.match(NUM_REGEX, line)
                if match is not None:
                    uc.num_models = int(match.group("num"))
                    uc.name = match.group("name")
                    unit.add_model_set(uc)
            elif line.startswith("◦ "):
                if uc is None:
                    raise ParseError(
                        "Tried to add wargear to non-existent UnitComposition", line
                    )
                _handle_unit_line(line, unit, uc)


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
