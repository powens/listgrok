import re
from listgrok.army.army_list import ArmyList, Unit, UnitComposition
from listgrok.parsers.parse_error import ParseError
from listgrok.parsers.helpers import count_leading_hashes


TITLE_REGEX = r"^(?P<superfaction>[\w\s]+) - (?P<faction>[\w\s]+) - (?P<list_name>[\w\s]+) - \[(?P<points>\d+) pts\]$"
ARMY_ROSTER_REGEX = r"^\+\+ Army Roster \+\+ \[(?P<points>\d+) pts\]$"
HEADER_REGEX = r"## (?P<title>[\w\s]+)$"

ARMY_ROSTER_BLOCK = r"""
    ^
    \# \+\+ Army Roster \+\+ \[(?P<points>\d+) pts\]
    \#\# Configuration
    Battle Size: (?P<battle_size>[\w\s]+) \((?P<battle_size_points>\d+) Point Limit\)
    Detachment: (?P<detachment>[\w\s]+)
    $
"""

UNIT_BLOCK = r"""
    ^
    \#\# (?P<unit_type>[\w\s]+) [\d+ pts\]]
"""
SINGLE_UNIT = r"""
    ^
    (?P<name>[\w\s]+) \[(?P<points>\d+) pts\]:
    (?:\n(?P<details>(?:.|\n)*?))?
    """


class NewRecruitGWParser:
    def _handle_header(self, lines: list[str]):
        header = "\n".join(lines)
        match = re.match(TITLE_REGEX, header, flags=re.MULTILINE)
        if match:
            self.list.super_faction = match.group("superfaction").strip()
            self.list.faction = match.group("faction").strip()
            self.list.name = match.group("list_name").strip()
            self.list.points = int(match.group("points"))
        else:
            raise ParseError("Invalid header format", lines)

    def _handle_configuration(self, lines: list[str]):
        config = "\n".join(lines)
        match = re.match(ARMY_ROSTER_REGEX, config, flags=re.MULTILINE)
        if match:
            self.list.points = int(match.group("points"))
        else:
            raise ParseError("Invalid army roster format", lines)

    def _handle_unit(self, lines: list[str]):
        pass

    def parse(self, list_text: str) -> ArmyList:
        self.list = ArmyList()
        self.state_machine = "HEADER"

        self.line_collection: list[str] = []

        for line in list_text.splitlines():
            if len(line.strip()) == 0:
                if len(self.line_collection) > 0:
                    match self.state_machine:
                        case "HEADER":
                            self._handle_header(self.line_collection)
                            self.state_machine = "CONFIG"
                        case "CONFIG":
                            self.state_machine = "UNIT"
                        case "UNIT":
                            self._handle_unit(self.line_collection)
                        case _:
                            raise ParseError("Unknown state", self.state_machine)

                    self.line_collection.clear()
                continue

            self.line_collection.append(line)
        return self.list
