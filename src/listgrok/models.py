"""The common data model that army-list parsers fill in.

Each dataclass exposes `to_dict()` with stable keys: optional fields are always
present, as `None`/`False`/`""`. `dataclasses.asdict` keeps that contract by
construction — every field is emitted, recursing into nested dataclasses.
"""

from dataclasses import asdict, dataclass, field


@dataclass
class Attachment:
    """How a unit joins an attached unit — GW's 11th edition leader/bodyguard pairing."""

    group: str = ""  # "Attached unit 1" — the group heading, verbatim
    role: str = ""  # "Leader" | "Bodyguard"
    role_detail: str = ""  # "Character" | "Battleline" | "" — the parenthetical

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UnitComposition:
    name: str
    num_models: int | None = None
    wargear: dict[str, int] = field(default_factory=dict)

    def add_wargear(self, weapon: str, count: int):
        if weapon not in self.wargear:
            self.wargear[weapon] = count
        else:
            self.wargear[weapon] += count

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Unit:
    name: str
    sheet_type: str = ""
    is_warlord: bool = False
    enhancement: str = ""
    points: int | None = None
    composition: list[UnitComposition] = field(default_factory=list)
    decorations: list[str] = field(default_factory=list)
    attachment: Attachment | None = None

    def add_model_set(self, model_set: UnitComposition):
        self.composition.append(model_set)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ArmyList:
    # Everything defaults because the parser's fold builds the list
    # incrementally, block by block.
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

    def to_dict(self) -> dict:
        return asdict(self)
