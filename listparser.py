import re

from dataclasses import dataclass
from typing import List

ARMY_NAME_REGEX = r"^(?P<name>.*)\s\((?P<points>\d+)\s[Pp]oints\)$"
NUM_REGEX = r"^(?P<num>\d+)x\s(?P<name>.*)$"
UNIT_TYPES = [
    "CHARACTERS",
    "OTHER DATASHEETS",
    "ALLIED UNITS",
    "BATTLELINE",
]


@dataclass
class Loadout:
    loadout_entry: List[str]


@dataclass
class UnitCompoision:
    num_models: int
    loadout: List[Loadout]


@dataclass
class Unit:
    name: str
    sheet_type: str
    is_warlord: bool
    points: int
    # composition: List[UnitCompoision]

    def __init__(self):
        self.name = ""
        self.sheet_type = ""
        self.is_warlord = False
        self.points = -1
        # self.composition = []


@dataclass
class List:
    name: str
    points: int
    super_faction: str
    faction: str
    detachment: str
    army_size: str
    units: List[Unit]

    def __init__(self):
        self.name = ""
        self.points = -1
        self.super_faction = ""
        self.faction = ""
        self.detachment = ""
        self.army_size = ""
        self.units = []


def _process_army_size(list: List, line: str) -> None:
    list.army_size = line


def _count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip())


class ListParser:
    def parse_list(self, list_text: str) -> List:
        self.list = List()
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
                case "DETACHMENT":
                    self._handle_detachment(line)
                case "UNIT_START":
                    self._handle_unit_start(line)

            self.prev_leading_spaces = _count_leading_spaces(line)
        return self.list

    def _handle_start(self, line: str):
        match = re.match(ARMY_NAME_REGEX, line)
        self.list.name = match.group("name")
        self.list.points = int(match.group("points"))
        self.state_machine = "FACTION"

    def _handle_faction(self, line: str):
        # We need to handle both factions with and without a super faction
        check_match = re.match(ARMY_NAME_REGEX, line)
        if check_match is None:
            self.faction_collection.append(line.strip())
        else:
            self.list.detachment = self.faction_collection[0]
            self.list.faction = self.faction_collection[1]
            if len(self.faction_collection) == 3:
                self.list.super_faction = self.faction_collection[2]
            self.list.army_size = line
            self.state_machine = "UNIT_START"

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
                # self.state_machine = "UNIT_CH"


def parse_wh_app_list(list_text: str) -> List:
    return ListParser().parse_list(list_text)


def parse_list(list: str) -> List:
    return parse_wh_app_list(list)


if __name__ == "__main__":
    with open("examples/example1.txt", "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list)

    with open("examples/example2.txt", "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list)
