import pytest

from listgrok.parsers.official_app import (
    _is_army_size_line,
    _count_leading_spaces,
    _handle_faction_collection,
    _handle_unit_block
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

class TestHandleUnitBlock:
    def test_single_character(self):
        list = ArmyList()
        assert len(list.units) == 0
        collection = [
            "Wolf Guard Battle Leader on Thunderwolf (95 Points)",
            "  • Warlord",
            "  • 1x Close combat weapon",
            "  • 1x Crushing teeth and claws",
            "  • 1x Power fist",
            "  • 1x Storm Shield",
            "  • Enhancements: Portents of Wisdom",
        ]
        _handle_unit_block(collection, "CHARACTERS", list)

        assert len(list.units) == 1
        unit = list.units[0]
        assert unit.name == "Wolf Guard Battle Leader on Thunderwolf"
        assert unit.points == 95
        assert unit.sheet_type == "CHARACTERS"
        assert unit.is_warlord
        assert unit.enhancement == "Portents of Wisdom"
        assert len(unit.composition) == 1
        uc = unit.composition[0]
        assert uc.name == ""
        assert uc.num_models == 1
        assert uc.wargear == {
            "Close combat weapon": 1,
            "Crushing teeth and claws": 1,
            "Power fist": 1,
            "Storm Shield": 1,
        }

    def test_multi_model_unit(self):
        list = ArmyList()
        assert len(list.units) == 0
        collection = [
            "Crisis Starscythe Battlesuits (110 Points)",
            "  • 1x Crisis Starscythe Shas’vre",
            "     ◦ 1x Battlesuit fists",
            "     ◦ 1x Gun Drone",
            "     ◦ 1x Marker Drone",
            "     ◦ 2x T’au flamer",
            "  • 2x Crisis Starscythe Shas’ui",
            "     ◦ 2x Battlesuit fists",
            "     ◦ 2x Gun Drone",
            "     ◦ 2x Shield Drone",
            "     ◦ 4x T’au flamer",
        ]
        _handle_unit_block(collection, "OTHER DATASHEETS", list)

        assert len(list.units) == 1
        unit = list.units[0]
        assert unit.name == "Crisis Starscythe Battlesuits"
        assert unit.points == 110
        assert unit.sheet_type == "OTHER DATASHEETS"
        assert not unit.is_warlord
        assert unit.enhancement == ""
        assert len(unit.composition) == 2
        uc = unit.composition[0]
        assert uc.name == "Crisis Starscythe Shas’vre"
        assert uc.num_models == 1
        assert uc.wargear == {
            "Battlesuit fists": 1,
            "Gun Drone": 1,
            "Marker Drone": 1,
            "T’au flamer": 2,
        }
        uc = unit.composition[1]
        assert uc.name == "Crisis Starscythe Shas’ui"
        assert uc.num_models == 2
        assert uc.wargear == {
            "Battlesuit fists": 2,
            "Gun Drone": 2,
            "Shield Drone": 2,
            "T’au flamer": 4,
        }