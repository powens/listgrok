from dataclasses import dataclass, field


@dataclass
class Attachment:
    """How a unit joins an attached unit — GW's 11th edition leader/bodyguard pairing."""

    group: str = ""  # "Attached unit 1" — the group heading, verbatim
    role: str = ""  # "Leader" | "Bodyguard"
    role_detail: str = ""  # "Character" | "Battleline" | "" — the parenthetical

    def to_json(self) -> dict:
        return {
            "group": self.group,
            "role": self.role,
            "role_detail": self.role_detail,
        }


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
    attachment: Attachment | None = None

    def add_model_set(self, model_set: UnitComposition):
        self.composition.append(model_set)

    def to_json(self) -> dict:
        o: dict = {
            "name": self.name,
            "sheet_type": self.sheet_type,
            "enhancement": self.enhancement,
            "points": self.points,
            "composition": [model.to_json() for model in self.composition],
            "decorations": self.decorations,
        }
        if self.is_warlord:
            o["is_warlord"] = self.is_warlord
        if self.attachment is not None:
            o["attachment"] = self.attachment.to_json()
        return o


@dataclass
class ArmyList:
    name: str = ""
    points: int | None = None
    super_faction: str = ""
    faction: str = ""
    detachments: list[str] = field(default_factory=list)
    detachment_points: int | None = None
    disposition: str = ""
    army_size: str = ""
    army_size_points: int | None = None
    units: list[Unit] = field(default_factory=list)

    def add_unit(self, unit: Unit):
        self.units.append(unit)

    def to_json(self) -> dict:
        o: dict = {
            "name": self.name,
            "points": self.points,
            "faction": self.faction,
            "detachments": self.detachments,
            "detachment_points": self.detachment_points,
            "disposition": self.disposition,
            "army_size": self.army_size,
            "army_size_points": self.army_size_points,
            "units": [unit.to_json() for unit in self.units],
        }
        if self.super_faction:
            o["super_faction"] = self.super_faction

        return o
