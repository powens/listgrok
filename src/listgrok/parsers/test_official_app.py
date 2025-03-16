import pytest

from listgrok.parsers.official_app import (
    _is_army_size_line,
    _count_leading_spaces,
    _handle_faction_collection,
)
from listgrok.army.army_list import ArmyList
from listgrok.parsers.parse_error import ParseError


@pytest.mark.parametrize(
    "line,expected",
    [
        ("Test Army (2000 Points)", True),
        ("Knights (1500 points)", True),
        ("Not an army line", False),
    ],
)
def test_is_army_size_line(line, expected):
    assert _is_army_size_line(line) == expected


@pytest.mark.parametrize(
    "line,expected",
    [
        ("foo", 0),
        ("  • 1x Dawn Blade", 2),
        ("     ◦ 1x Marksman bolt carbine", 5),
    ],
)
def test_count_leading_spaces(line, expected):
    assert _count_leading_spaces(line) == expected


class TestHandleFaction:
    def test_3_lines(self):
        list = ArmyList()
        collection = [
            "T’au Empire",
            "Retaliation Cadre",
            "Strike Force (2000 Points)",
        ]

        _handle_faction_collection(collection, list)

        assert list.faction == "T’au Empire"
        assert list.super_faction == ""
        assert list.detachment == "Retaliation Cadre"
        assert list.army_size == "Strike Force (2000 Points)"

    def test_4_lines(self):
        list = ArmyList()
        collection = [
            "Space Marines",
            "Space Wolves",
            "Stormlance Task Force",
            "Strike Force (2000 Points)",
        ]

        _handle_faction_collection(collection, list)

        assert list.faction == "Space Wolves"
        assert list.super_faction == "Space Marines"
        assert list.detachment == "Stormlance Task Force"
        assert list.army_size == "Strike Force (2000 Points)"

    def test_too_few_lines(self):
        list = ArmyList()
        collection = [
            "Space Marines",
            "Stormlance Task Force",
        ]

        with pytest.raises(ParseError):
            _handle_faction_collection(collection, list)

    def test_too_many_lines(self):
        list = ArmyList()
        collection = [
            "Space Marines",
            "Stormlance Task Force",
            "foo",
            "baz",
            "bar",
        ]

        with pytest.raises(ParseError):
            _handle_faction_collection(collection, list)
