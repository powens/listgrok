from pathlib import Path

import pytest

from listgrok.army.army_list import ArmyList
from listgrok.parsers.helpers import UNIT_TYPES
from listgrok.parsers.parse_error import ParseError
from listgrok.parsers.official_app import (
    _parse_faction_block,
    build_tree,
    parse_official_app,
    parse_unit_block,
)

EXAMPLES = Path(__file__).parents[2] / "examples" / "official_app"


class TestBuildTree:
    def test_flat_single_model(self):
        roots = build_tree(
            [
                "  • 1x Heavy flamer",
                "  • 1x Helfrost cannon",
                "  • 1x Trueclaw",
            ]
        )
        assert len(roots) == 3
        assert [n.text for n in roots] == [
            "1x Heavy flamer",
            "1x Helfrost cannon",
            "1x Trueclaw",
        ]
        assert all(n.indent == 2 for n in roots)
        assert all(n.children == [] for n in roots)

    def test_nested_multi_model_dialect_a(self):
        roots = build_tree(
            [
                "  • 1x Infiltrator Sergeant",
                "     ◦ 1x Bolt pistol",
                "     ◦ 1x Close combat weapon",
                "  • 4x Infiltrator",
                "     ◦ 4x Bolt pistol",
            ]
        )
        assert len(roots) == 2
        assert roots[0].text == "1x Infiltrator Sergeant"
        assert [c.text for c in roots[0].children] == [
            "1x Bolt pistol",
            "1x Close combat weapon",
        ]
        assert roots[1].text == "4x Infiltrator"
        assert [c.text for c in roots[1].children] == ["4x Bolt pistol"]

    def test_dialect_b_bulletless_continuation_promoted(self):
        # official_7 "Acolyte Iconward": a bulletless line indented deeper than
        # the bullet it follows is a sibling of that bullet, not a child.
        roots = build_tree(
            [
                "  • 1x Autopistol",
                "    1x Cult claws",
                "  • Enhancement: Deeds that Speak to the Masses",
            ]
        )
        assert len(roots) == 3
        assert [n.text for n in roots] == [
            "1x Autopistol",
            "1x Cult claws",
            "Enhancement: Deeds that Speak to the Masses",
        ]
        assert all(n.children == [] for n in roots)

    def test_dialect_b_nested_bullets_and_continuation(self):
        # official_7 "Acolyte Hybrids": nested • marks wargear, and bulletless
        # continuation lines belong to the same model as the bullet above them.
        roots = build_tree(
            [
                "  • 1x Acolyte Leader",
                "    • 1x Autopistol",
                "      1x Leader’s bio-weapons",
                "  • 4x Acolyte Hybrid",
                "    • 1x Cult Icon",
                "      1x Cult claws and knife",
                "      3x Heavy mining tool",
            ]
        )
        assert len(roots) == 2
        assert roots[0].text == "1x Acolyte Leader"
        assert [c.text for c in roots[0].children] == [
            "1x Autopistol",
            "1x Leader’s bio-weapons",
        ]
        assert roots[1].text == "4x Acolyte Hybrid"
        assert [c.text for c in roots[1].children] == [
            "1x Cult Icon",
            "1x Cult claws and knife",
            "3x Heavy mining tool",
        ]


class TestParseUnitBlock:
    def test_single_model_dialect_a(self):
        army_list = ArmyList()
        parse_unit_block(
            [
                "Wolf Guard Battle Leader on Thunderwolf (95 Points)",
                "  • Warlord",
                "  • 1x Close combat weapon",
                "  • 1x Crushing teeth and claws",
                "  • Enhancements: Portents of Wisdom",
            ],
            "CHARACTERS",
            army_list,
        )

        assert len(army_list.units) == 1
        unit = army_list.units[0]
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
        }

    def test_multi_model_dialect_a(self):
        army_list = ArmyList()
        parse_unit_block(
            [
                "Crisis Starscythe Battlesuits (110 Points)",
                "  • 1x Crisis Starscythe Shas’vre",
                "     ◦ 1x Battlesuit fists",
                "     ◦ 2x T’au flamer",
                "  • 2x Crisis Starscythe Shas’ui",
                "     ◦ 2x Battlesuit fists",
                "     ◦ 4x T’au flamer",
            ],
            "OTHER DATASHEETS",
            army_list,
        )

        unit = army_list.units[0]
        assert unit.name == "Crisis Starscythe Battlesuits"
        assert unit.points == 110
        assert not unit.is_warlord
        assert len(unit.composition) == 2
        assert unit.composition[0].name == "Crisis Starscythe Shas’vre"
        assert unit.composition[0].num_models == 1
        assert unit.composition[0].wargear == {
            "Battlesuit fists": 1,
            "T’au flamer": 2,
        }
        assert unit.composition[1].name == "Crisis Starscythe Shas’ui"
        assert unit.composition[1].num_models == 2
        assert unit.composition[1].wargear == {
            "Battlesuit fists": 2,
            "T’au flamer": 4,
        }

    def test_single_model_dialect_b(self):
        # official_7 Acolyte Iconward: bulletless continuation, singular Enhancement
        army_list = ArmyList()
        parse_unit_block(
            [
                "Acolyte Iconward (75 points)",
                "  • 1x Autopistol",
                "    1x Cult claws",
                "  • Enhancement: Deeds that Speak to the Masses",
            ],
            "CHARACTERS",
            army_list,
        )

        unit = army_list.units[0]
        assert unit.name == "Acolyte Iconward"
        assert unit.points == 75
        assert unit.enhancement == "Deeds that Speak to the Masses"
        assert len(unit.composition) == 1
        uc = unit.composition[0]
        assert uc.name == unit.name
        assert uc.num_models == 1
        assert uc.wargear == {"Autopistol": 1, "Cult claws": 1}

    def test_multi_model_dialect_b(self):
        # official_7 Atalan Jackals: nested bullets plus bulletless continuation
        army_list = ArmyList()
        parse_unit_block(
            [
                "Atalan Jackals (85 points)",
                "  • 4x Atalan Jackal",
                "    • 2x Atalan power weapon",
                "      3x Atalan small arms",
                "      2x Close combat weapon",
                "      1x Grenade launcher",
                "  • 1x Atalan Wolfquad",
                "    • 1x Atalan small arms",
                "      1x Close combat weapon",
                "      1x Mining laser",
            ],
            "OTHER DATASHEETS",
            army_list,
        )

        unit = army_list.units[0]
        assert len(unit.composition) == 2
        assert unit.composition[0].name == "Atalan Jackal"
        assert unit.composition[0].num_models == 4
        assert unit.composition[0].wargear == {
            "Atalan power weapon": 2,
            "Atalan small arms": 3,
            "Close combat weapon": 2,
            "Grenade launcher": 1,
        }
        assert unit.composition[1].name == "Atalan Wolfquad"
        assert unit.composition[1].num_models == 1
        assert unit.composition[1].wargear == {
            "Atalan small arms": 1,
            "Close combat weapon": 1,
            "Mining laser": 1,
        }

    def test_single_model_decoration(self):
        # official_4 Daemon Prince: a non-Nx, non-Warlord/Enhancement line
        army_list = ArmyList()
        parse_unit_block(
            [
                "Daemon Prince of Chaos with Wings (200 Points)",
                "  • Daemonic Allegiance: Tzeentch",
                "  • 1x Hellforged weapons",
                "  • Enhancements: Neverblade",
            ],
            "CHARACTERS",
            army_list,
        )

        unit = army_list.units[0]
        assert unit.enhancement == "Neverblade"
        assert unit.decorations == ["Daemonic Allegiance: Tzeentch"]
        assert unit.composition[0].wargear == {"Hellforged weapons": 1}


class TestParseFactionBlock:
    def test_dialect_a_with_super_faction(self):
        army_list = ArmyList()
        _parse_faction_block(
            [
                "Space Marines",
                "Space Wolves",
                "Stormlance Task Force",
                "Strike Force (2000 Points)",
            ],
            army_list,
        )
        assert army_list.super_faction == "Space Marines"
        assert army_list.faction == "Space Wolves"
        assert army_list.detachment == "Stormlance Task Force"
        assert army_list.army_size == "Strike Force (2000 Points)"

    def test_dialect_a_no_super_faction(self):
        army_list = ArmyList()
        _parse_faction_block(
            [
                "T’au Empire",
                "Retaliation Cadre",
                "Strike Force (2000 Points)",
            ],
            army_list,
        )
        assert army_list.super_faction == ""
        assert army_list.faction == "T’au Empire"
        assert army_list.detachment == "Retaliation Cadre"
        assert army_list.army_size == "Strike Force (2000 Points)"

    def test_dialect_b_army_size_in_middle(self):
        # official_6/official_7 order: faction, army_size, detachment
        army_list = ArmyList()
        _parse_faction_block(
            [
                "Genestealer Cults",
                "Strike Force (2000 points)",
                "Xenocreed Congregation",
            ],
            army_list,
        )
        assert army_list.super_faction == ""
        assert army_list.faction == "Genestealer Cults"
        assert army_list.detachment == "Xenocreed Congregation"
        assert army_list.army_size == "Strike Force (2000 points)"

    def test_no_army_size_line_raises(self):
        with pytest.raises(ParseError):
            _parse_faction_block(["Space Marines", "Space Wolves"], ArmyList())


class TestParseOfficialAppV2:
    def test_dialect_a_official_1(self):
        army_list = parse_official_app((EXAMPLES / "official_1.txt").read_text())

        assert army_list.name == "Boop"
        assert army_list.points == 1985
        assert army_list.super_faction == "Space Marines"
        assert army_list.faction == "Space Wolves"
        assert army_list.detachment == "Stormlance Task Force"
        assert army_list.army_size == "Strike Force (2000 Points)"
        assert len(army_list.units) == 14

        bjorn = army_list.units[0]
        assert bjorn.name == "Bjorn the Fell-Handed"
        assert bjorn.points == 190
        assert bjorn.sheet_type == "CHARACTERS"
        assert len(bjorn.composition) == 1
        assert bjorn.composition[0].num_models == 1
        assert bjorn.composition[0].wargear == {
            "Heavy flamer": 1,
            "Helfrost cannon": 1,
            "Trueclaw": 1,
        }

        infiltrators = army_list.units[8]
        assert infiltrators.name == "Infiltrator Squad"
        assert infiltrators.sheet_type == "OTHER DATASHEETS"
        assert len(infiltrators.composition) == 2
        assert infiltrators.composition[0].name == "Infiltrator Sergeant"
        assert infiltrators.composition[0].num_models == 1
        assert infiltrators.composition[1].name == "Infiltrator"
        assert infiltrators.composition[1].num_models == 4
        assert infiltrators.composition[1].wargear == {
            "Bolt pistol": 4,
            "Close combat weapon": 4,
            "Marksman bolt carbine": 4,
        }

    def test_dialect_b_official_7(self):
        army_list = parse_official_app((EXAMPLES / "official_7.txt").read_text())

        assert army_list.name == "1. I Have Friends Everywhere. Very Fragile Friends."
        assert army_list.points == 2000
        assert army_list.faction == "Genestealer Cults"
        assert army_list.detachment == "Xenocreed Congregation"
        assert army_list.army_size == "Strike Force (2000 points)"
        assert len(army_list.units) == 24

        iconward = army_list.units[0]
        assert iconward.name == "Acolyte Iconward"
        assert iconward.points == 75
        assert iconward.enhancement == "Deeds that Speak to the Masses"
        assert len(iconward.composition) == 1
        assert iconward.composition[0].num_models == 1
        assert iconward.composition[0].wargear == {"Autopistol": 1, "Cult claws": 1}

        jackals = army_list.units[17]
        assert jackals.name == "Atalan Jackals"
        assert jackals.sheet_type == "OTHER DATASHEETS"
        assert len(jackals.composition) == 2
        assert jackals.composition[0].name == "Atalan Jackal"
        assert jackals.composition[0].num_models == 4
        assert jackals.composition[0].wargear == {
            "Atalan power weapon": 2,
            "Atalan small arms": 3,
            "Close combat weapon": 2,
            "Grenade launcher": 1,
        }
        assert jackals.composition[1].name == "Atalan Wolfquad"
        assert jackals.composition[1].num_models == 1


# Faction-level metadata for every example list. official_3 has no army-name
# header (name == "", points == None) and exercises the headerless-list path.
OFFICIAL_EXAMPLES = {
    "official_1.txt": {
        "name": "Boop",
        "points": 1985,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachment": "Stormlance Task Force",
        "army_size": "Strike Force (2000 Points)",
        "unit_count": 14,
    },
    "official_2.txt": {
        "name": "Midlife crisis 2",
        "points": 2000,
        "super_faction": "",
        "faction": "T’au Empire",
        "detachment": "Retaliation Cadre",
        "army_size": "Strike Force (2000 Points)",
        "unit_count": 20,
    },
    "official_3.txt": {
        "name": "",
        "points": None,
        "super_faction": "",
        "faction": "Thousand Sons",
        "detachment": "Changehost of Deceit",
        "army_size": "Strike Force (2000 points)",
        "unit_count": 10,
    },
    "official_4.txt": {
        "name": "Daemons(Tzeentch)",
        "points": 1995,
        "super_faction": "",
        "faction": "Chaos Daemons",
        "detachment": "Scintillating Legion",
        "army_size": "Strike Force (2,000 Points)",
        "unit_count": 14,
    },
    "official_5.txt": {
        "name": "Blood claws unite",
        "points": 1990,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachment": "Saga of the Beastslayer",
        "army_size": "Strike Force (2,000 Points)",
        "unit_count": 11,
    },
    "official_6.txt": {
        "name": "Siege Saboteurs",
        "points": 1990,
        "super_faction": "",
        "faction": "Chaos Space Marines",
        "detachment": "Nightmare Hunt",
        "army_size": "Strike Force (2000 points)",
        "unit_count": 15,
    },
    "official_7.txt": {
        "name": "1. I Have Friends Everywhere. Very Fragile Friends.",
        "points": 2000,
        "super_faction": "",
        "faction": "Genestealer Cults",
        "detachment": "Xenocreed Congregation",
        "army_size": "Strike Force (2000 points)",
        "unit_count": 24,
    },
    "official_8.txt": {
        "name": "Aaaa crisis",
        "points": 1995,
        "super_faction": "",
        "faction": "T’au Empire",
        "detachment": "Retaliation Cadre",
        "army_size": "Strike Force (2,000 Points)",
        "unit_count": 18,
    },
}


class TestAllOfficialExamples:
    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_metadata(self, filename):
        expected = OFFICIAL_EXAMPLES[filename]
        army_list = parse_official_app((EXAMPLES / filename).read_text())

        assert army_list.name == expected["name"]
        assert army_list.points == expected["points"]
        assert army_list.super_faction == expected["super_faction"]
        assert army_list.faction == expected["faction"]
        assert army_list.detachment == expected["detachment"]
        assert army_list.army_size == expected["army_size"]
        assert len(army_list.units) == expected["unit_count"]

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_units_well_formed(self, filename):
        army_list = parse_official_app((EXAMPLES / filename).read_text())

        for unit in army_list.units:
            assert unit.name, f"{filename}: unit with empty name"
            assert isinstance(unit.points, int)
            assert unit.sheet_type in UNIT_TYPES
            assert unit.composition, f"{filename}: {unit.name} has no composition"
            for uc in unit.composition:
                assert uc.name, f"{filename}: {unit.name} composition with empty name"
                assert all(count > 0 for count in uc.wargear.values())
