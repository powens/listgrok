import pytest

from listgrok.parsers.official_app.units import build_tree, parse_unit
from listgrok.parsers.parse_error import ParseError


class TestBuildTree:
    def test_flat_body_has_no_children(self):
        # official_1 Ghostkeel Battlesuit
        roots = build_tree(
            [
                "  • 1x Battlesuit Support System",
                "  • 1x Fusion collider",
                "  • 1x Ghostkeel fists",
            ]
        )

        assert [node.text for node in roots] == [
            "1x Battlesuit Support System",
            "1x Fusion collider",
            "1x Ghostkeel fists",
        ]
        assert all(node.children == [] for node in roots)

    def test_deeper_indent_nests(self):
        # official_1 Vespid Stingwings
        roots = build_tree(
            [
                "  • 1x Vespid Strain Leader",
                "     ◦ 1x Neutron blaster",
                "     ◦ 1x Stingwing claws",
                "  • 4x Vespid Stingwing",
                "     ◦ 4x Neutron blaster",
            ]
        )

        assert len(roots) == 2
        assert roots[0].text == "1x Vespid Strain Leader"
        assert [child.text for child in roots[0].children] == [
            "1x Neutron blaster",
            "1x Stingwing claws",
        ]
        assert roots[1].text == "4x Vespid Stingwing"
        assert [child.text for child in roots[1].children] == ["4x Neutron blaster"]


class TestParseUnit:
    def test_single_model_unit_gets_one_implicit_model_set(self):
        # official_1 Ghostkeel Battlesuit
        unit = parse_unit(
            [
                "Ghostkeel Battlesuit (150 Points)",
                "  • 1x Battlesuit Support System",
                "  • 1x Fusion collider",
                "  • 1x Ghostkeel fists",
                "  • 1x Twin fusion blaster",
            ],
            "OTHER DATASHEETS",
        )

        assert unit.name == "Ghostkeel Battlesuit"
        assert unit.points == 150
        assert unit.sheet_type == "OTHER DATASHEETS"
        assert unit.attachment is None
        assert len(unit.composition) == 1
        assert unit.composition[0].name == "Ghostkeel Battlesuit"
        assert unit.composition[0].num_models == 1
        assert unit.composition[0].wargear == {
            "Battlesuit Support System": 1,
            "Fusion collider": 1,
            "Ghostkeel fists": 1,
            "Twin fusion blaster": 1,
        }

    def test_multi_model_unit_gets_one_model_set_per_root(self):
        # official_1 Kroot Carnivores
        unit = parse_unit(
            [
                "Kroot Carnivores (65 Points)",
                "  • 1x Long-quill",
                "     ◦ 1x Close combat weapon",
                "     ◦ 1x Kroot pistol",
                "     ◦ 1x Kroot rifle",
                "  • 9x Kroot Carnivore",
                "     ◦ 9x Close combat weapon",
                "     ◦ 9x Kroot rifle",
            ],
            "OTHER DATASHEETS",
        )

        assert len(unit.composition) == 2
        assert unit.composition[0].name == "Long-quill"
        assert unit.composition[0].num_models == 1
        assert unit.composition[0].wargear == {
            "Close combat weapon": 1,
            "Kroot pistol": 1,
            "Kroot rifle": 1,
        }
        assert unit.composition[1].name == "Kroot Carnivore"
        assert unit.composition[1].num_models == 9
        assert unit.composition[1].wargear == {
            "Close combat weapon": 9,
            "Kroot rifle": 9,
        }

    def test_warlord_and_attachment_and_repeated_wargear(self):
        # official_1 Commander in Enforcer Battlesuit: the app writes the four
        # missile pods as two lines.
        unit = parse_unit(
            [
                "Commander in Enforcer Battlesuit (80 Points)",
                "  • Attached as: Leader (Character)",
                "  • Warlord",
                "  • 1x Battlesuit fists",
                "  • 1x Missile pod",
                "  • 3x Missile pod",
                "  • 2x Shield Drone",
            ],
            "ATTACHED UNITS",
        )

        assert unit.is_warlord
        assert unit.attachment is not None
        assert unit.attachment.role == "Leader"
        assert unit.attachment.role_detail == "Character"
        assert unit.attachment.group == ""  # stamped by the fold, not here
        assert unit.composition[0].wargear == {
            "Battlesuit fists": 1,
            "Missile pod": 4,
            "Shield Drone": 2,
        }

    def test_bodyguard_attachment_with_empty_detail(self):
        # official_1 Crisis Fireknife Battlesuits
        unit = parse_unit(
            [
                "Crisis Fireknife Battlesuits (130 Points)",
                "  • Attached as: Bodyguard ()",
                "  • 1x Crisis Fireknife Shas’vre",
                "     ◦ 1x Battlesuit fists",
                "  • 2x Crisis Fireknife Shas’ui",
                "     ◦ 2x Battlesuit fists",
            ],
            "ATTACHED UNITS",
        )

        assert unit.attachment is not None
        assert unit.attachment.role == "Bodyguard"
        assert unit.attachment.role_detail == ""
        assert len(unit.composition) == 2

    def test_enhancement_keeps_its_parenthetical(self):
        # official_2 Captain in Terminator Armour
        unit = parse_unit(
            [
                "Captain in Terminator Armour (100 Points)",
                "  • 1x Combi-weapon",
                "  • 1x Relic fist",
                "  • Enhancements: Thirst for Glory (Upgrade)",
            ],
            "CHARACTERS",
        )

        assert unit.enhancement == "Thirst for Glory (Upgrade)"
        assert unit.composition[0].wargear == {"Combi-weapon": 1, "Relic fist": 1}

    def test_singular_enhancement_label_is_accepted(self):
        unit = parse_unit(
            [
                "Captain in Terminator Armour (100 Points)",
                "  • 1x Combi-weapon",
                "  • Enhancement: Thirst for Glory",
            ],
            "CHARACTERS",
        )

        assert unit.enhancement == "Thirst for Glory"

    def test_unrecognised_body_line_becomes_a_decoration(self):
        # Synthetic: no 11th fixture has one yet, but 10th ed exports carried
        # lines like this and the model keeps an escape hatch for them.
        unit = parse_unit(
            [
                "Ghostkeel Battlesuit (150 Points)",
                "  • Daemonic Allegiance: Tzeentch",
                "  • 1x Ghostkeel fists",
            ],
            "OTHER DATASHEETS",
        )

        assert unit.decorations == ["Daemonic Allegiance: Tzeentch"]
        assert unit.composition[0].wargear == {"Ghostkeel fists": 1}

    def test_unrecognised_nested_root_becomes_a_decoration(self):
        # Synthetic: no 11th fixture has a nested (multi-model) unit whose
        # root line fails NUM_REGEX, but the parser must not fabricate a
        # UnitComposition(num_models=None) for one — it goes to decorations,
        # mirroring the flat-body case above and what _add_wargear already
        # does for an unrecognised child line.
        unit = parse_unit(
            [
                "Kroot Carnivores (65 Points)",
                "  • Something odd",
                "     ◦ 1x Kroot rifle",
                "  • 9x Kroot Carnivore",
                "     ◦ 9x Kroot rifle",
            ],
            "OTHER DATASHEETS",
        )

        assert unit.decorations == ["Something odd"]
        assert len(unit.composition) == 1
        assert unit.composition[0].name == "Kroot Carnivore"
        assert unit.composition[0].num_models == 9
        assert unit.composition[0].wargear == {"Kroot rifle": 9}

    def test_comma_formatted_unit_points(self):
        unit = parse_unit(
            ["Titanic Thing (1,000 Points)", "  • 1x Big gun"], "CHARACTERS"
        )

        assert unit.points == 1000

    def test_unparseable_header_raises(self):
        with pytest.raises(ParseError):
            parse_unit(["Ghostkeel Battlesuit", "  • 1x Ghostkeel fists"], "CHARACTERS")

    def test_empty_block_raises(self):
        with pytest.raises(ParseError):
            parse_unit([], "CHARACTERS")
