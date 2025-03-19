from dataclasses import dataclass
from typing import List

@dataclass
class UnitComposition:
    name: str
    num_models: int
    wargear: dict[str, int]

    def __init__(self):
        self.name = ""
        self.num_models = -1
        self.wargear = {}

    def add_wargear(self, weapon: str, count: int):
        if weapon not in self.wargear:
            self.wargear[weapon] = count
        else:
            self.wargear[weapon] += count


@dataclass
class Unit:
    name: str
    sheet_type: str
    is_warlord: bool
    enhancement: str
    points: int
    composition: List[UnitComposition]

    def __init__(self):
        self.name = ""
        self.sheet_type = ""
        self.is_warlord = False
        self.enhancement = ""
        self.points = -1
        self.composition = []

    def add_model_set(self, model_set: UnitComposition):
        self.composition.append(model_set)

@dataclass
class ArmyList:
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

    def add_unit(self, unit: Unit):
        self.units.append(unit)