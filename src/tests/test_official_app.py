import pytest

from listgrok.parsers.official_app import (
    _is_army_size_line,
    _handle_faction_collection,
    _handle_unit_block,
    parse_official_app,
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
        assert uc.name == unit.name
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


class TestOfficialAppParser:
    def test_happy_path(self):
        list_text = """
Test list (405 Points)

Space Marines
Space Wolves
Champions of Fenris
Strike Force (2000 Points)

CHARACTERS

Wolf Lord on Thunderwolf (120 Points)
  • Warlord
  • 1x Close combat weapon
  • 1x Crushing teeth and claws
  • 1x Power fist
  • 1x Relic Shield
  • Enhancements: Longstrider

BATTLELINE

Assault Intercessor Squad (75 Points)
  • 1x Assault Intercessor Sergeant
     ◦ 1x Plasma pistol
     ◦ 1x Power fist
  • 4x Assault Intercessor
     ◦ 4x Astartes chainsword
     ◦ 4x Heavy bolt pistol

DEDICATED TRANSPORTS

Impulsor (80 Points)
  • 1x Armoured hull
  • 1x Ironhail heavy stubber
  • 1x Orbital Comms Array (Aura)
  • 2x Storm bolter

OTHER DATASHEETS

Fenrisian Wolves (30 Points)
  • 5x Fenrisian Wolf
     ◦ 5x Teeth and claws

ALLIED UNITS

Callidus Assassin (100 Points)
  • 1x Neural shredder
  • 1x Phase sword and poison blades

Exported with App Version: v1.29.1 (1), Data Version: v581
        """

        list = parse_official_app(list_text)

        assert list.name == "Test list"
        assert list.points == 405
        assert list.super_faction == "Space Marines"
        assert list.faction == "Space Wolves"
        assert list.detachment == "Champions of Fenris"
        assert list.army_size == "Strike Force (2000 Points)"
        assert len(list.units) == 5

        unit = list.units[0]
        assert unit.name == "Wolf Lord on Thunderwolf"
        assert unit.points == 120
        assert unit.sheet_type == "CHARACTERS"
        assert unit.is_warlord
        assert unit.enhancement == "Longstrider"
        assert len(unit.composition) == 1
        uc = unit.composition[0]
        assert uc.name == unit.name
        assert uc.num_models == 1
        assert uc.wargear == {
            "Close combat weapon": 1,
            "Crushing teeth and claws": 1,
            "Power fist": 1,
            "Relic Shield": 1,
        }

        unit = list.units[1]
        assert unit.name == "Assault Intercessor Squad"
        assert unit.points == 75
        assert unit.sheet_type == "BATTLELINE"
        assert not unit.is_warlord
        assert unit.enhancement == ""
        assert len(unit.composition) == 2
        uc = unit.composition[0]
        assert uc.name == "Assault Intercessor Sergeant"
        assert uc.num_models == 1
        assert uc.wargear == {
            "Plasma pistol": 1,
            "Power fist": 1,
        }
        uc = unit.composition[1]
        assert uc.name == "Assault Intercessor"
        assert uc.num_models == 4
        assert uc.wargear == {
            "Astartes chainsword": 4,
            "Heavy bolt pistol": 4,
        }

        unit = list.units[2]
        assert unit.name == "Impulsor"
        assert unit.points == 80
        assert unit.sheet_type == "DEDICATED TRANSPORTS"
        assert not unit.is_warlord
        assert unit.enhancement == ""
        assert len(unit.composition) == 1
        uc = unit.composition[0]
        assert uc.name == unit.name
        assert uc.num_models == 1
        assert uc.wargear == {
            "Armoured hull": 1,
            "Ironhail heavy stubber": 1,
            "Orbital Comms Array (Aura)": 1,
            "Storm bolter": 2,
        }

        unit = list.units[3]
        assert unit.name == "Fenrisian Wolves"
        assert unit.points == 30
        assert unit.sheet_type == "OTHER DATASHEETS"
        assert not unit.is_warlord
        assert unit.enhancement == ""
        assert len(unit.composition) == 1
        uc = unit.composition[0]
        assert uc.name == "Fenrisian Wolf"
        assert uc.num_models == 5

        unit = list.units[4]
        assert unit.name == "Callidus Assassin"
        assert unit.points == 100
        assert unit.sheet_type == "ALLIED UNITS"
        assert not unit.is_warlord
        assert unit.enhancement == ""
        assert len(unit.composition) == 1
        uc = unit.composition[0]
        assert uc.name == unit.name
        assert uc.num_models == 1
        assert uc.wargear == {
            "Neural shredder": 1,
            "Phase sword and poison blades": 1,
        }

    def test_no_units(self):
        list_text = """
Test list (405 Points)

Space Marines
Space Wolves
Champions of Fenris
Strike Force (2000 Points)

Exported with App Version: v1.29.1 (1), Data Version: v581
        """

        list = parse_official_app(list_text)

        assert list.name == "Test list"
        assert list.points == 405
        assert list.super_faction == "Space Marines"
        assert list.faction == "Space Wolves"
        assert list.detachment == "Champions of Fenris"
        assert list.army_size == "Strike Force (2000 Points)"
        assert len(list.units) == 0

    def test_no_unittype(self):
        list_text = """
Test list (405 Points)

Space Marines
Space Wolves
Champions of Fenris
Strike Force (2000 Points)

Wolf Lord on Thunderwolf (120 Points)
  • Warlord
  • 1x Close combat weapon
  • 1x Crushing teeth and claws
  • 1x Power fist
  • 1x Relic Shield
  • Enhancements: Longstrider

Exported with App Version: v1.29.1 (1), Data Version: v581
        """

        with pytest.raises(ParseError) as e:
            parse_official_app(list_text)
        assert e.value.message == "No unit type found"

    def test_multiline_list_name(self):
        list_text = """
Test list
1234 (405 Points)

Space Marines
Space Wolves
Champions of Fenris
Strike Force (2000 Points)
        """

        list = parse_official_app(list_text)
        assert list.name == "Test list\n1234"
        assert list.points == 405
        assert list.super_faction == "Space Marines"
        assert list.faction == "Space Wolves"
        assert list.detachment == "Champions of Fenris"
        assert list.army_size == "Strike Force (2000 Points)"
        assert len(list.units) == 0

    @pytest.mark.skip("Not sure how to handle this case yet")
    def test_invalid_unit(self):
        list_text = """
Test list (405 Points)

Space Marines
Space Wolves
Champions of Fenris
Strike Force (2000 Points)

CHARACTERS

Wolf Lord on Thunderwolf (120 Points)
  • Warlord
  • 1x Close combat weapon
  • 1x Crushing teeth and claws
  • 1x Power fist
  • 1x Relic Shield
  • Enhancements: Longstrider
     ◦ 5x Teeth and claws

Exported with App Version: v1.29.1 (1), Data Version: v581
        """

        list = parse_official_app(list_text)
        # with pytest.raises(ParseError) as e:

        assert list.name == "Test list"
        assert list.points == 405
        assert list.super_faction == "Space Marines"
        assert list.faction == "Space Wolves"
        assert list.detachment == "Champions of Fenris"
        assert list.army_size == "Strike Force (2000 Points)"
        assert len(list.units) == 1

        unit = list.units[0]
        assert unit.name == "Wolf Lord on Thunderwolf"
        assert unit.points == 120
        assert unit.sheet_type == "CHARACTERS"
        assert unit.is_warlord
        assert unit.enhancement == "Longstrider"
        assert len(unit.composition) == 1
        uc = unit.composition[0]
        assert uc.name == unit.name
        assert uc.num_models == 1
        assert uc.wargear == {
            "Close combat weapon": 1,
            "Crushing teeth and claws": 1,
            "Power fist": 1,
            "Relic Shield": 1,
        }

        # assert e.value.message == "No unit type found"
