from dataclasses import dataclass


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

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "num_models": self.num_models,
            "wargear": self.wargear,
        }


@dataclass
class Unit:
    name: str
    sheet_type: str
    is_warlord: bool
    enhancement: str
    points: int
    composition: list[UnitComposition]

    def __init__(self):
        self.name = ""
        self.sheet_type = ""
        self.is_warlord = False
        self.enhancement = ""
        self.points = -1
        self.composition = []

    def add_model_set(self, model_set: UnitComposition):
        self.composition.append(model_set)

    def to_json(self) -> dict:
        o = {
            "name": self.name,
            "sheet_type": self.sheet_type,
            "enhancement": self.enhancement,
            "points": self.points,
            "composition": [model.to_json() for model in self.composition],
        }
        if self.is_warlord:
            o["is_warlord"] = self.is_warlord
        return o


@dataclass
class ArmyList:
    name: str
    points: int
    super_faction: str
    faction: str
    detachment: str
    army_size: str
    units: list[Unit]

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

    def to_json(self) -> dict:
        o = {
            "name": self.name,
            "points": self.points,
            "faction": self.faction,
            "detachment": self.detachment,
            "army_size": self.army_size,
            "units": [unit.to_json() for unit in self.units],
        }
        if self.super_faction:
            o["super_faction"] = self.super_faction

        return o
