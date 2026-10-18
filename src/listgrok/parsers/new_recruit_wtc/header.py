"""Parse the `+`-ruled header block of a New Recruit WTC export."""

import re
from collections.abc import Sequence

from listgrok.exceptions import ParseError
from listgrok.models import ArmyList

RULE_REGEX = re.compile(r"^\+{10,}$")
_KEY_REGEX = re.compile(r"^\+ (?P<key>[A-Z][A-Z ]*): ?(?P<value>.*)$")
_POINTS_REGEX = re.compile(r"^(?P<points>\d+)\s*pts$")
_RULE_SUFFIX_REGEX = re.compile(r"\s*\([^()]*\)$")
# Detachment names that themselves contain a comma — the only one among 222
# distinct names across the 649 LVO 2026 lists. A new one splits wrongly until
# it is added here.
NAMES_WITH_COMMAS = ("Ordo Xenos, Alien Hunters",)
_DETACHMENT_NAME_REGEX = re.compile(
    r"\s*(?:" + "|".join(map(re.escape, NAMES_WITH_COMMAS)) + r"|[^,]+)"
)


def parse_header(lines: Sequence[str], army_list: ArmyList) -> int | None:
    """Fill the header fields of `army_list` from the lines between the rules.

    Returns the declared `NUMBER OF UNITS`, or None when the header has none.
    """
    values = _header_values(lines)

    if "FACTION KEYWORD" not in values:
        raise ParseError("Header has no FACTION KEYWORD line", lines)
    parts = [part.strip() for part in values["FACTION KEYWORD"].split(" - ")]
    # `Alliance - [Parent - ]Faction`: the leading alliance (Imperium, Chaos,
    # Xenos) has no counterpart in the official app's export, so only a parent
    # faction fills super_faction — matching that parser's Space Wolves ->
    # Space Marines.
    army_list.faction = parts[-1]
    if len(parts) > 2:
        army_list.super_faction = parts[-2]

    if "TOTAL ARMY POINTS" not in values:
        raise ParseError("Header has no TOTAL ARMY POINTS line", lines)
    points = _POINTS_REGEX.match(values["TOTAL ARMY POINTS"])
    if points is None:
        raise ParseError("Unreadable TOTAL ARMY POINTS", values["TOTAL ARMY POINTS"])
    army_list.points = int(points.group("points"))

    if "DETACHMENT" in values:
        army_list.detachments = split_detachments(values["DETACHMENT"])
    army_list.disposition = values.get("FORCE DISPOSITION", "")

    declared = values.get("NUMBER OF UNITS")
    if declared is None:
        return None
    if not declared.isdigit():
        raise ParseError("Unreadable NUMBER OF UNITS", declared)
    return int(declared)


def split_detachments(value: str) -> list[str]:
    """`A, B (Rule)` -> `["A", "B"]`: drop the trailing rule, split on commas.

    A name from NAMES_WITH_COMMAS is matched whole before any comma splits it.
    """
    names = _DETACHMENT_NAME_REGEX.findall(_RULE_SUFFIX_REGEX.sub("", value))
    return [name.strip() for name in names if name.strip()]


def _header_values(lines: Sequence[str]) -> dict[str, str]:
    """Map each `+ KEY: value` line to its value.

    A bare `+` is a spacer; a line starting `&` continues the previous key
    (New Recruit wraps a multi-unit ENHANCEMENT line that way) and is dropped,
    since no continued key is stored.
    """
    values: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if line in ("", "+") or line.startswith("&"):
            continue
        match = _KEY_REGEX.match(line)
        if match is None:
            raise ParseError("Unrecognised header line", line)
        values[match.group("key")] = match.group("value").replace("\xa0", " ").strip()
    return values
