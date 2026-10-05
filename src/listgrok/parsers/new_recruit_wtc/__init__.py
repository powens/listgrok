"""Parse army lists in New Recruit's WTC export format (newrecruit.eu).

Framed by `+` rules: the header between them, the units after, and an optional
`Created with newrecruit.eu` footer. Units are grouped line by line — blank
lines carry no meaning in this format — and leader/bodyguard pairs are matched
up after every unit is parsed.
"""

import re
from collections.abc import Sequence

from listgrok.exceptions import ParseError
from listgrok.models import ArmyList, Attachment, Unit
from listgrok.parsers.new_recruit_wtc.header import RULE_REGEX, parse_header
from listgrok.parsers.new_recruit_wtc.units import UnitLinks, is_unit_header, parse_unit

__all__ = ["parse_new_recruit_wtc"]

_FOOTER_PREFIX = "Created with newrecruit.eu"
_REFERENCE_REGEX = re.compile(r"^(?P<name>.+?)(?:\[(?P<index>\d+)\])?$")


def parse_new_recruit_wtc(list_text: str) -> ArmyList:
    header, body = _frame(list_text.splitlines())
    army_list = ArmyList()
    declared_units = parse_header(header, army_list)

    links: list[UnitLinks] = []
    for unit_header, unit_body in _group_units(body):
        unit, unit_links = parse_unit(unit_header, unit_body)
        army_list.add_unit(unit)
        links.append(unit_links)

    if declared_units is not None and len(army_list.units) != declared_units:
        raise ParseError(
            f"Header declares {declared_units} units but the list has "
            f"{len(army_list.units)}"
        )
    _pair_attachments(army_list.units, links)
    return army_list


def _frame(lines: Sequence[str]) -> tuple[list[str], list[str]]:
    """Split the export into header lines and body lines, dropping the rest."""
    rules = [i for i, line in enumerate(lines) if RULE_REGEX.match(line.strip())]
    if len(rules) < 2:
        raise ParseError("No +++ ruled header block")
    opening, closing = rules[0], rules[1]

    body = []
    for line in lines[closing + 1 :]:
        if line.strip().startswith(_FOOTER_PREFIX):
            break
        body.append(line)
    return list(lines[opening + 1 : closing]), body


def _group_units(body: Sequence[str]) -> list[tuple[str, list[str]]]:
    """Group body lines under the unit header line above them."""
    units: list[tuple[str, list[str]]] = []
    for line in body:
        if not line.strip():
            continue
        if is_unit_header(line):
            units.append((line, []))
        elif not units:
            raise ParseError("Body line before the first unit", line)
        else:
            units[-1][1].append(line)
    return units


def _pair_attachments(units: Sequence[Unit], links: Sequence[UnitLinks]) -> None:
    """Stamp an `Attachment` on every unit in a leader/bodyguard group.

    Either side's line alone makes the link; a bodyguard may have several
    leaders, but a leader leads only one bodyguard. Groups are numbered in the
    file order of their bodyguards.
    """
    leaders_of: dict[int, set[int]] = {}
    for index, unit_links in enumerate(links):
        for reference in unit_links.leading:
            leaders_of.setdefault(_resolve(reference, units), set()).add(index)
        for reference in unit_links.attached_to:
            leaders_of.setdefault(index, set()).add(_resolve(reference, units))

    led_by: dict[int, int] = {}
    for bodyguard, leaders in leaders_of.items():
        for leader in leaders:
            if led_by.setdefault(leader, bodyguard) != bodyguard:
                raise ParseError("Leader attached to two units", units[leader].name)

    for number, bodyguard in enumerate(sorted(leaders_of), start=1):
        group = f"Attached unit {number}"
        units[bodyguard].attachment = Attachment(group=group, role="Bodyguard")
        for leader in sorted(leaders_of[bodyguard]):
            units[leader].attachment = Attachment(group=group, role="Leader")


def _resolve(reference: str, units: Sequence[Unit]) -> int:
    """`Name[n]` -> index of the nth unit named Name; bare `Name` must be unique."""
    match = _REFERENCE_REGEX.match(reference)
    if match is None:
        # Unreachable in practice: the pattern matches any non-empty string,
        # and a reference is never empty. Kept so a bad edit fails loudly.
        raise ParseError("Unreadable attachment reference", reference)
    candidates = [i for i, unit in enumerate(units) if unit.name == match.group("name")]
    if match.group("index") is not None:
        position = int(match.group("index"))
        if not 1 <= position <= len(candidates):
            raise ParseError("Unresolvable attachment reference", reference)
        return candidates[position - 1]
    if len(candidates) != 1:
        raise ParseError("Unresolvable attachment reference", reference)
    return candidates[0]
