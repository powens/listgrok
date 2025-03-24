import re
from listgrok.army.army_list import ArmyList, Unit, UnitComposition
from listgrok.parsers.parse_error import ParseError
from listgrok.parsers.helpers import count_leading_spaces

FACTION_REGEX = r"^\+ FACTION KEYWORD: (?P<faction>.+)$"
DETACHMENT_REGEX = r"^\+ DETACHMENT: (?P<detachment>.+)$"
POINTS_REGEX = r"^\+ TOTAL ARMY POINTS: (?P<points>.+)pts$"
UNIT_NAME_REGEX = r"^(?P<num>\d+)x\s(?P<name>.+)\s\((?P<points>\d+)\spts\)$"
ENHANCEMENT_REGEX = r"^(?P<name>.+) \(\+[0-9]+ pts\)$"
LOADOUT_REGEX = r"^(?P<num>\d+)x\s(?P<name>.+)$"

UNIT_TYPES = [
    "CHARACTER",
    "BATTLELINE",
    "DEDICATED TRANSPORT",
    "OTHER DATASHEETS",
]
    

def _handle_header(lines: list[str], list: ArmyList):
    header = "\n".join(lines)
    matches = [
        # ("list_name", "")
        ("points", POINTS_REGEX, int),
        ("faction", FACTION_REGEX, str),
        ("detachment", DETACHMENT_REGEX, str),
    ]

    for (key, regex, type) in matches:
        match = re.search(regex, header, flags=re.MULTILINE)
        if match is not None:
            val = type(match.group(key))
            setattr(list, key, val)


def _handle_unit_line(line: str, unit: Unit, uc: UnitComposition):
    leading_spaces = count_leading_spaces(line)
    line = line.strip().lstrip("• ")
    if line == "Warlord":
        unit.is_warlord = True
    elif line.endswith("pts)"):
        match = re.match(ENHANCEMENT_REGEX, line, flags=re.MULTILINE)
        if match is not None:
            unit.enhancement = match.group("name")
    elif line.endswith("upgrade"):
        # Ignore any line that ends with upgrade. It looks like duplicate enhancement text
        return
    elif leading_spaces == 2:
        wargear = line.split(",")
        for w in wargear:
            uc.add_wargear(w.strip(), 1)
    else:
        match = re.match(LOADOUT_REGEX, line)
        if match is None:
            raise ParseError("Unexpected loadout line", line)
        uc.add_wargear(match.group("name"), int(match.group("num")))


def _handle_unit(lines: list[str], list: ArmyList, unit_type: str):
    if len(lines) == 0:
        return
    
    most_leading_spaces = 0
    for line in lines:
        leading_spaces = count_leading_spaces(line)
        if leading_spaces > most_leading_spaces:
            most_leading_spaces = leading_spaces
        
    unit = Unit()
    first_line = lines[0]
    match = re.match(UNIT_NAME_REGEX, first_line)
    if match is None:
        raise ParseError("Unexpected unit line", first_line)
    unit.name = match.group("name")
    unit.points = int(match.group("points"))
    unit.sheet_type = unit_type
    list.add_unit(unit)

    if most_leading_spaces == 0:
        uc = UnitComposition()
        uc.name = unit.name
        uc.num_models = 1
        unit.add_model_set(uc)
        for line in lines[1:]:
            _handle_unit_line(line, unit, uc)
    elif most_leading_spaces == 4:
        uc = UnitComposition()
        for line in lines[1:]:
            leading_spaces = count_leading_spaces(line)
            if leading_spaces == 0:
                uc = UnitComposition()
                
                match = re.match(LOADOUT_REGEX, line.lstrip("• "))
                if match is None:
                    raise ParseError("Unexpected unit line", line)

                uc.name = match.group("name")
                uc.num_models = int(match.group("num"))
                unit.add_model_set(uc)

            elif leading_spaces == 2:
                _handle_unit_line(line, unit, uc)
            elif leading_spaces == 4:
                _handle_unit_line(line, unit, uc)
            else:
                raise ParseError(f"Unexpected leading spaces: {leading_spaces}", line)
    else:
        raise ParseError(f"Unexpected most leading spaces: {most_leading_spaces}", lines)
    

class NewRecruitParser:
    def parse(self, list_text: str) -> ArmyList:
        self.list = ArmyList()
        self.state_machine = "HEADER"
        self.last_unit_type = ""
        self.line_collection = []

        for line in list_text.split("\n"):
            if len(line.strip()) == 0:
                if len(self.line_collection) > 0:
                    match self.state_machine:
                        case "HEADER":
                            _handle_header(self.line_collection, self.list)
                            self.state_machine = "UNIT"
                        case "UNIT":
                            _handle_unit(self.line_collection, self.list, self.last_unit_type)
                    self.line_collection.clear()
                continue

            if line in UNIT_TYPES:
                self.last_unit_type = line
                continue
            
            self.line_collection.append(line)

        return self.list
    