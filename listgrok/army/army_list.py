from dataclasses import dataclass
from typing import List


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
