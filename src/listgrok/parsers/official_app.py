import re
from listgrok.army.army_list import Unit, ArmyList, UnitComposition
from listgrok.parsers.parse_error import ParseError

ARMY_NAME_REGEX = r"^(?P<name>.*)\s\((?P<points>\d+)\s[Pp]oints\)$"
NUM_REGEX = r"^(?P<num>\d+)x\s(?P<name>.*)$"
UNIT_TYPES = [
    "CHARACTERS",
    "OTHER DATASHEETS",
    "ALLIED UNITS",
    "BATTLELINE",
    "DEDICATED TRANSPORTS",
]


def _is_army_size_line(line: str) -> bool:
    return re.match(ARMY_NAME_REGEX, line) is not None


def _count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip())


def _handle_faction_collection(collection: list[str], list: ArmyList):
    line_count = len(collection)
    if line_count < 3 or line_count > 4:
        raise ParseError("Unexpected faction line", collection[0])

    list.army_size = collection[-1]
    list.detachment = collection[-2]

    if line_count == 4:
        list.super_faction = collection[0]
        list.faction = collection[1]
    else:
        list.faction = collection[0]

def _handle_unit_block(lines: list[str], most_recent_unit_type: str, list: ArmyList):
    # Determine if this is a single model or multiple model unit
    most_leading_spaces = 0
    for line in lines:
        leading_spaces = _count_leading_spaces(line)
        if leading_spaces > most_leading_spaces:
            most_leading_spaces = leading_spaces

    unit = Unit()

    first_line = lines[0]
    match = re.match(ARMY_NAME_REGEX, first_line)
    if match is None:
        raise ValueError("Unexpected unit_start", first_line)
        return
    unit.name = match.group("name")
    unit.points = int(match.group("points"))
    unit.sheet_type = most_recent_unit_type

    list.add_unit(unit)

    if most_leading_spaces == 2:
        uc = UnitComposition()
        uc.num_models = 1
        unit.add_model_set(uc)
        for line in lines:
            line = line.strip().lstrip("• ")

            if line == "Warlord":
                unit.is_warlord = True
            elif line.startswith("Enhancements: "):
                unit.enhancement = line[len("Enhancements: "):]
            else:
                match = re.match(NUM_REGEX, line)
                if match is not None:
                    count=int(match.group("num"))
                    name=match.group("name")
                    uc.add_wargear(name, count)
                else:
                    print("Wargear Parser unexpected line", line)
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
                line = line.lstrip("◦ ")
                match = re.match(NUM_REGEX, line)
                if match is not None:
                    count=int(match.group("num"))
                    name=match.group("name")
                    if uc is None:
                        print("Wargear Parser unexpected wargear", line)
                    else:
                        uc.add_wargear(name, count) 


class OfficialAppListParser:
    def parse_list(self, list_text: str) -> ArmyList:
        self.list = ArmyList()
        self.state_machine = "START"
        self.line_collection = []

        self.prev_leading_spaces = 0
        for line in list_text.split("\n"):
            if len(line) == 0:
                continue

            if line.startswith("Exported with App Version:"):
                continue

            match self.state_machine:
                case "START":
                    self._handle_start(line)
                case "FACTION":
                    self._handle_faction(line)
                case "UNIT_START":
                    self._handle_unit_start(line)
                case "UNIT_DETAILS":
                    self._handle_unit_details(line)

            self.prev_leading_spaces = _count_leading_spaces(line)
        return self.list

    def _handle_start(self, line: str):
        match = re.match(ARMY_NAME_REGEX, line)
        if match is None:
            raise ParseError("Expected army name", line)
        self.list.name = match.group("name")
        self.list.points = int(match.group("points"))
        self.state_machine = "FACTION"

    def _handle_faction(self, line: str):
        # We need to handle both factions with and without a super faction
        if line in UNIT_TYPES:
            _handle_faction_collection(self.line_collection, self.list)
            self.line_collection = []

            self.state_machine = "UNIT_START"
            self._handle_unit_start(line)
        else:
            self.line_collection.append(line)

    def _handle_unit_start(self, line: str):
        if line in UNIT_TYPES:
            self.most_recent_unit_type = line.strip()
        else:
            leading_spaces = _count_leading_spaces(line)

            if leading_spaces == 0:
                self.current_unit = Unit()
                match = re.match(ARMY_NAME_REGEX, line)
                if match is None:
                    raise ValueError("Unexpected unit_start", line)
                    return
                self.current_unit.name = match.group("name")
                self.current_unit.points = int(match.group("points"))
                self.current_unit.sheet_type = self.most_recent_unit_type

                self.list.units.append(self.current_unit)
                self.state_machine = "UNIT_DETAILS"
            else:
                print("Unexpected unit_start", line)

    def _handle_unit_details(self, line: str):
        if _count_leading_spaces(line) == 0:
            _handle_unit_block(self.line_collection, self.most_recent_unit_type, self.list)
            self.line_collection = []
            self.state_machine = "UNIT_START"
            self._handle_unit_start(line)
        else:
            self.line_collection.append(line)
