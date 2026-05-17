from dataclasses import dataclass, field


@dataclass
class UnitComposition:
    name: str = ""
    num_models: int | None = None
    wargear: dict[str, int] = field(default_factory=dict)

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
    name: str = ""
    sheet_type: str = ""
    is_warlord: bool = False
    enhancement: str = ""
    points: int | None = None
    composition: list[UnitComposition] = field(default_factory=list)
    decorations: list[str] = field(default_factory=list)

    def add_model_set(self, model_set: UnitComposition):
        self.composition.append(model_set)

    def to_json(self) -> dict:
        o = {
            "name": self.name,
            "sheet_type": self.sheet_type,
            "enhancement": self.enhancement,
            "points": self.points,
            "composition": [model.to_json() for model in self.composition],
            "decorations": self.decorations,
        }
        if self.is_warlord:
            o["is_warlord"] = self.is_warlord
        return o


@dataclass
class ArmyList:
    name: str = ""
    points: int | None = None
    super_faction: str = ""
    faction: str = ""
    detachment: str = ""
    army_size: str = ""
    units: list[Unit] = field(default_factory=list)

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
