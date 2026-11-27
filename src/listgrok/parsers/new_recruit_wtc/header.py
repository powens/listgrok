"""Parse the `+`-ruled header block of a New Recruit WTC export."""

import re
from collections.abc import Sequence

from listgrok.exceptions import ParseError
from listgrok.models import ArmyList
from listgrok.parsers.official_app.detachment_names import COMPOUND_DETACHMENTS

RULE_REGEX = re.compile(r"^\+{10,}$")
_KEY_REGEX = re.compile(r"^\+ (?P<key>[A-Z][A-Z ]*): ?(?P<value>.*)$")
_POINTS_REGEX = re.compile(r"^(?P<points>\d+)\s*pts$")
# A detachment's rule in parentheses, allowing one level of nesting:
# `(Rule)`, `(Rule (Aura))`. No detachment name contains a parenthesis.
_RULE_REGEX = re.compile(r"\s*\((?:[^()]|\([^()]*\))*\)")
# Detachment names that themselves contain a comma (the Ordo detachments), taken
# from the official-app parser's list so both parsers grow together. Longest
# first, so a name that prefixes another cannot win the alternation.
NAMES_WITH_COMMAS = tuple(
    sorted(
        (name for name in COMPOUND_DETACHMENTS if ", " in name), key=len, reverse=True
    )
)


def _detachment_name_regex(names_with_commas: Sequence[str]) -> re.Pattern[str]:
    """A name from `names_with_commas` ending at a comma or the end, else up to
    the next comma. An empty tuple leaves only the comma split, so no empty
    alternative can match first and swallow every name."""
    plain = r"[^,]+"
    if not names_with_commas:
        return re.compile(r"\s*(?:" + plain + ")")
    whole = "|".join(map(re.escape, names_with_commas))
    return re.compile(r"\s*(?:(?:" + whole + r")(?=\s*(?:,|$))|" + plain + ")")


_DETACHMENT_NAME_REGEX = _detachment_name_regex(NAMES_WITH_COMMAS)
_NUMBER_REGEX = re.compile(r"\d+")
# New Recruit names a faction by its keyword; the official app by its codex
# name. Unlisted names pass through verbatim.
_FACTION_NAMES = {
    "Adeptus Astartes": "Space Marines",
    "Heretic Astartes": "Chaos Space Marines",
}


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
    # faction fills super_faction. Both take the official app's name for a
    # faction (Adeptus Astartes -> Space Marines).
    army_list.faction = _FACTION_NAMES.get(parts[-1], parts[-1])
    if len(parts) > 2:
        army_list.super_faction = _FACTION_NAMES.get(parts[-2], parts[-2])

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
    if not _NUMBER_REGEX.fullmatch(declared):
        raise ParseError("Unreadable NUMBER OF UNITS", declared)
    return int(declared)


def split_detachments(value: str) -> list[str]:
    """`A (RuleA), B (RuleB)` -> `["A", "B"]`: drop every rule, split on commas.

    A name from NAMES_WITH_COMMAS is matched whole before any comma splits it,
    but only when it is the whole name: `Ordo Xenos, Alien Hunters Extended`
    is not the Ordo detachment.
    """
    names = _DETACHMENT_NAME_REGEX.findall(_RULE_REGEX.sub("", value))
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
