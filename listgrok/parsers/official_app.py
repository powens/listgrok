import re
from listgrok.army.army_list import Unit, ArmyList
from listgrok.game_data import get_factions, get_all_detachments

ARMY_NAME_REGEX = r"^(?P<name>.*)\s\((?P<points>\d+)\s[Pp]oints\)$"
NUM_REGEX = r"^(?P<num>\d+)x\s(?P<name>.*)$"
UNIT_TYPES = [
    "CHARACTERS",
    "OTHER DATASHEETS",
    "ALLIED UNITS",
    "BATTLELINE",
    "DEDICATED TRANSPORTS",
]
SUPER_FACTIONS = ["Space Marines"]


def _is_army_size_line(line: str) -> bool:
    return re.match(ARMY_NAME_REGEX, line) is not None


def _is_superfaction_line(line: str) -> bool:
    return line in SUPER_FACTIONS


def _is_faction_line(line: str) -> bool:
    return line.replace("’", "'") in get_factions()


def _is_detachment_line(line: str) -> bool:
    return line in get_all_detachments()


def _count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip())


class ListParser:
    def parse_list(self, list_text: str) -> ArmyList:
        self.list = ArmyList()
        self.state_machine = "START"
        self.faction_collection = []

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
        self.list.name = match.group("name")
        self.list.points = int(match.group("points"))
        self.state_machine = "FACTION"

    def _handle_faction(self, line: str):
        # We need to handle both factions with and without a super faction
        if _is_army_size_line(line):
            self.list_army_size = line
        elif _is_detachment_line(line):
            self.list.detachment = line
        elif _is_faction_line(line):
            self.list.faction = line
        elif _is_superfaction_line(line):
            self.list.super_faction = line
        elif line in UNIT_TYPES:
            self.state_machine = "UNIT_START"
            self._handle_unit_start(line)
        else:
            print(f"Unknown faction line: {line}")

    def _handle_unit_start(self, line: str):
        if line in UNIT_TYPES:
            self.most_recent_unit_type = line.strip()
        else:
            leading_spaces = _count_leading_spaces(line)

            if leading_spaces == 0:
                self.current_unit = Unit()
                match = re.match(ARMY_NAME_REGEX, line)
                self.current_unit.name = match.group("name")
                self.current_unit.points = int(match.group("points"))
                self.current_unit.sheet_type = self.most_recent_unit_type

                self.list.units.append(self.current_unit)
                # self.state_machine = "UNIT_DETAILS"
            else:
                pass
                # print("Unexpected unit_start", line)

    def _handle_unit_details(self, line: str):
        # if leading
        pass
