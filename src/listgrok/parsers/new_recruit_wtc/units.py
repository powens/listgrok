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


def is_body_line(line: str) -> bool:
    """A unit header, or a body line of a form only a unit body carries."""
    text = line.strip()
    return (
        is_unit_header(text)
        or _BULLET_REGEX.match(text) is not None
        or _WITH_REGEX.match(text) is not None
        or _ENHANCEMENT_REGEX.match(text) is not None
        or text.startswith((_LEADING_PREFIX, _ATTACHED_PREFIX))
    )


def parse_unit(header: str, body: Sequence[str]) -> tuple[Unit, UnitLinks]:
    match = UNIT_HEADER_REGEX.match(header.strip())
    if match is None:
        raise ParseError("Unparseable unit header", header)

    unit = Unit(name=match.group("name"), points=int(match.group("points")))
    links = UnitLinks()
    inline = _split_items(match.group("inline") or "")

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
            if unit.enhancement:
                # A unit takes one enhancement; keep any further line visible
                # rather than silently replacing the first.
                unit.decorations.append(line)
            else:
                unit.enhancement = enhancement.group("name")
        elif line.startswith(_LEADING_PREFIX):
            links.leading.append(line.removeprefix(_LEADING_PREFIX))
        elif line.startswith(_ATTACHED_PREFIX):
            links.attached_to.append(line.removeprefix(_ATTACHED_PREFIX))
        else:
            unit.decorations.append(line)

    _add_header_items(unit, match, inline)
    return unit, links


def _add_header_items(unit: Unit, header: re.Match[str], items: list[str]) -> None:
    """Credit the header line's items to the model set they describe.

    Without bullets that is the unit's one implicit model set. With bullets it
    is the bullet named after the unit; if there is not exactly one, the
    items stay visible as decorations rather than landing on the wrong model.
    `Warlord` is lifted either way.
    """
    if "Warlord" in items:
        unit.is_warlord = True
        items = [item for item in items if item != "Warlord"]
    if not unit.composition:
        _add_items(unit, _implicit_model_set(unit, header), items)
        return
    named = [model_set for model_set in unit.composition if model_set.name == unit.name]
    if len(named) == 1:
        _add_items(unit, named[0], items)
    else:
        unit.decorations.extend(items)


def _implicit_model_set(unit: Unit, header: re.Match[str]) -> UnitComposition:
    """The single model set of a unit with no bullets, named after the unit."""
    model_set = UnitComposition(name=unit.name, num_models=int(header.group("count")))
    unit.add_model_set(model_set)
    return model_set


def _split_commas(text: str) -> list[str]:
    """Split on commas outside parentheses: `A (x, y), B` -> `["A (x, y)", "B"]`."""
    items, depth, current = [], 0, []
    for char in text:
        if char == "," and depth == 0:
            items.append("".join(current))
            current = []
            continue
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        current.append(char)
    items.append("".join(current))
    return [item.strip() for item in items if item.strip()]


def _split_items(text: str) -> list[str]:
    """Split a wargear list on commas — but a `K with A, B` item owns the rest."""
    items = _split_commas(text)
    for i, item in enumerate(items):
        if _WITH_REGEX.match(item):
            return [*items[:i], ", ".join(items[i:])]
    return items


def _add_items(unit: Unit, model_set: UnitComposition, items: Sequence[str]) -> None:
    for item in items:
        if item == "Warlord":
            unit.is_warlord = True
        elif (with_item := _WITH_REGEX.match(item)) is not None:
            models = int(with_item.group("count"))
            for weapon in _split_commas(with_item.group("items")):
                if weapon == "Warlord":
                    unit.is_warlord = True
                elif (counted := _COUNTED_REGEX.match(weapon)) is not None:
                    # `4 with 2x Lightning claws`: two each, eight in all.
                    count = models * int(counted.group("count"))
                    model_set.add_wargear(counted.group("name"), count)
                else:
                    model_set.add_wargear(weapon, models)
        elif (counted := _COUNTED_REGEX.match(item)) is not None:
            model_set.add_wargear(counted.group("name"), int(counted.group("count")))
        elif item[0].isdigit():
            # "2 Storm Bolters" (nr_wtc_9): a number with neither "x" nor
            # "with" — kept visible rather than guessed into a count.
            unit.decorations.append(item)
        else:
            model_set.add_wargear(item, 1)
