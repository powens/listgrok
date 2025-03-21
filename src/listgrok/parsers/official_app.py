import re
from listgrok.army.army_list import Unit, ArmyList, UnitComposition
from listgrok.parsers.parse_error import ParseError

POINTS_LABEL_REGEX = r"^(?P<name>.+)\s\((?P<points>\d+)\s[Pp]oints\)$"
NUM_REGEX = r"^(?P<num>\d+)x\s(?P<name>.*)$"
UNIT_TYPES = [
    "CHARACTERS",
    "OTHER DATASHEETS",
    "ALLIED UNITS",
    "BATTLELINE",
    "DEDICATED TRANSPORTS",
]


def _is_army_size_line(line: str) -> bool:
    return re.match(POINTS_LABEL_REGEX, line) is not None


def _count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip())


def _handle_faction_collection(collection: list[str], list: ArmyList):
    line_count = len(collection)
    if line_count < 3 or line_count > 4:
        raise ParseError(f"line_count is {line_count}. Expected [3,4]", collection)

    list.army_size = collection[-1]
    list.detachment = collection[-2]

    if line_count == 4:
        list.super_faction = collection[0]
        list.faction = collection[1]
    else:
        list.faction = collection[0]


def _handle_unit_line(line: str, unit: Unit, uc: UnitComposition):
    line = line.strip().lstrip("• ").lstrip("◦ ")

    if line == "Warlord":
        unit.is_warlord = True
    elif line.startswith("Enhancements: "):
        unit.enhancement = line[len("Enhancements: ") :]
    else:
        match = re.match(NUM_REGEX, line)
        if match is None:
            raise ParseError("Unexpected unit line", line)

        count = int(match.group("num"))
        name = match.group("name")
        uc.add_wargear(name, count)

# TODO: Refactor this
def _handle_unit_block(lines: list[str], unit_type: str, list: ArmyList):
    # Determine if this is a single model or multiple model unit
    most_leading_spaces = 0
    for line in lines:
        leading_spaces = _count_leading_spaces(line)
        if leading_spaces > most_leading_spaces:
            most_leading_spaces = leading_spaces

    unit = Unit()

    first_line = lines[0]
    match = re.match(POINTS_LABEL_REGEX, first_line)
    if match is None:
        raise ValueError("Unexpected unit_start", first_line)
        return
    unit.name = match.group("name")
    unit.points = int(match.group("points"))
    unit.sheet_type = unit_type

    list.add_unit(unit)

    if most_leading_spaces == 2:
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
                line = line.lstrip("• ")
                uc = UnitComposition()

                match = re.match(NUM_REGEX, line)
                if match is not None:
                    uc.num_models = int(match.group("num"))
                    uc.name = match.group("name")
                    unit.add_model_set(uc)
            elif line.startswith("◦ "):
                if uc is None:
                    raise ParseError("Tried to add wargear to non-existent UnitComposition", line)
                _handle_unit_line(line, unit, uc)


class OfficialAppParser:
    def parse(self, list_text: str) -> ArmyList:
        self.list = ArmyList()
        self.state_machine = "START"
        self.line_collection = []
        self.most_recent_unit_type = ""

        for line in list_text.split("\n"):
            if len(line.strip()) == 0:
                # We've reached the end of a chunk of list. Handle it
                if len(self.line_collection) > 0:
                    match self.state_machine:
                        case "START":
                            self._handle_start(self.line_collection)
                        case "FACTION":
                            self._handle_faction(self.line_collection)
                        case "UNIT_DETAILS":
                            self._handle_unit_details(self.line_collection)

                    self.line_collection.clear()
                continue
            

            if line.startswith("Exported with App Version:"):
                continue

            if self._check_handle_unit_type(line):
                continue

            self.line_collection.append(line)

        return self.list

    def _handle_start(self, lines: list[str]):
        line = "\n".join(lines).strip()
        # Need re.DOTALL here because some army lists have newlines in them, for some reason
        match = re.match(POINTS_LABEL_REGEX, line, flags=re.DOTALL)
        if match is None:
            raise ParseError("Expected army name", line)
        self.list.name = match.group("name")
        self.list.points = int(match.group("points"))
        self.state_machine = "FACTION"

    def _handle_faction(self, lines: list[str]):
        # We need to handle both factions with and without a super faction
        _handle_faction_collection(lines, self.list)
        self.state_machine = "UNIT_DETAILS"

    def _check_handle_unit_type(self, line: str) -> bool:
        if line in UNIT_TYPES:
            self.most_recent_unit_type = line
            return True
        return False

    def _handle_unit_details(self, lines: list[str]):
        if self.most_recent_unit_type == "":
            raise ParseError("No unit type found", lines)
        
        _handle_unit_block(
            lines, self.most_recent_unit_type, self.list
        )
