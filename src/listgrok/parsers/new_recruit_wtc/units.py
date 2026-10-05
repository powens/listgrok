"""Parse one unit of a New Recruit WTC export: its header line and body lines.

Body lines are classified after stripping leading whitespace — the export's
indentation is not reliable enough to carry structure (a character's `Leading`
line is indented when it has bullets, a bodyguard's `Enhancement:` sometimes).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from listgrok.exceptions import ParseError
from listgrok.models import Unit, UnitComposition

UNIT_HEADER_REGEX = re.compile(
    r"^(?:Char\d+: )?(?P<count>\d+)x (?P<name>.+?) \((?P<points>\d+) pts\)"
    r"(?:: (?P<inline>.*))?$"
)
_BULLET_REGEX = re.compile(r"^• (?P<count>\d+)x (?P<name>.+?)(?:: (?P<items>.*))?$")
_WITH_REGEX = re.compile(r"^(?P<count>\d+) with (?P<items>.+)$")
_COUNTED_REGEX = re.compile(r"^(?P<count>\d+)x (?P<name>.+)$")
_ENHANCEMENT_REGEX = re.compile(r"^Enhancement: (?P<name>.+?) \(\+\d+ pts\)$")
_LEADING_PREFIX = "Leading "
_ATTACHED_PREFIX = "Attached to "


@dataclass
class UnitLinks:
    """The raw attachment references a unit's body carries, unresolved."""

    leading: list[str] = field(default_factory=list)
    attached_to: list[str] = field(default_factory=list)


def is_unit_header(line: str) -> bool:
    return UNIT_HEADER_REGEX.match(line.strip()) is not None


def parse_unit(header: str, body: Sequence[str]) -> tuple[Unit, UnitLinks]:
    match = UNIT_HEADER_REGEX.match(header.strip())
    if match is None:
        raise ParseError("Unparseable unit header", header)

    unit = Unit(name=match.group("name"), points=int(match.group("points")))
    links = UnitLinks()
    inline = _split_items(match.group("inline") or "")
    if "Warlord" in inline:
        unit.is_warlord = True
        inline = [item for item in inline if item != "Warlord"]

    model_set: UnitComposition | None = None
    for raw in body:
        line = raw.strip()
        if not line:
            continue
        if (bullet := _BULLET_REGEX.match(line)) is not None:
            model_set = UnitComposition(
                name=bullet.group("name"), num_models=int(bullet.group("count"))
            )
            unit.add_model_set(model_set)
            _add_items(unit, model_set, _split_items(bullet.group("items") or ""))
        elif _WITH_REGEX.match(line) is not None:
            if model_set is None:
                model_set = _implicit_model_set(unit, match)
            _add_items(unit, model_set, [line])
        elif (enhancement := _ENHANCEMENT_REGEX.match(line)) is not None:
            unit.enhancement = enhancement.group("name")
        elif line.startswith(_LEADING_PREFIX):
            links.leading.append(line.removeprefix(_LEADING_PREFIX))
        elif line.startswith(_ATTACHED_PREFIX):
            links.attached_to.append(line.removeprefix(_ATTACHED_PREFIX))
        else:
            unit.decorations.append(line)

    if not unit.composition:
        _implicit_model_set(unit, match)
    _add_items(unit, unit.composition[0], inline)
    return unit, links


def _implicit_model_set(unit: Unit, header: re.Match[str]) -> UnitComposition:
    """The single model set of a unit with no bullets, named after the unit."""
    model_set = UnitComposition(name=unit.name, num_models=int(header.group("count")))
    unit.add_model_set(model_set)
    return model_set


def _split_items(text: str) -> list[str]:
    """Split a wargear list on commas — but a `K with A, B` item owns the rest."""
    text = text.strip()
    if not text:
        return []
    if _WITH_REGEX.match(text):
        return [text]
    return [item.strip() for item in text.split(",") if item.strip()]


def _add_items(unit: Unit, model_set: UnitComposition, items: Sequence[str]) -> None:
    for item in items:
        if (with_item := _WITH_REGEX.match(item)) is not None:
            count = int(with_item.group("count"))
            for weapon in with_item.group("items").split(","):
                model_set.add_wargear(weapon.strip(), count)
        elif (counted := _COUNTED_REGEX.match(item)) is not None:
            model_set.add_wargear(counted.group("name"), int(counted.group("count")))
        elif item[0].isdigit():
            # "2 Storm Bolters" (nr_wtc_9): a number with neither "x" nor
            # "with" — kept visible rather than guessed into a count.
            unit.decorations.append(item)
        else:
            model_set.add_wargear(item, 1)
