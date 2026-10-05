import pytest

from listgrok import ParseError
from listgrok.parsers.official_app.units import build_tree, parse_unit


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

    def test_bullet_run_body_nests_runs_under_the_last_counted_root(self):
        # official_3 Gretchin: the newer dialect writes every line at column
        # zero; a bulleted line followed by another bulleted line is a root,
        # and a bullet-then-plain run holds the wargear of the root above it.
        roots = build_tree(
            [
                "• 10x Gretchin",
                "• 10x Close combat weapon",
                "10x Grot blasta",
                "• 1x Runtherd",
                "• 1x Runtherd tools",
                "1x Slugga",
            ]
        )

        assert [node.text for node in roots] == ["10x Gretchin", "1x Runtherd"]
        assert [child.text for child in roots[0].children] == [
            "10x Close combat weapon",
            "10x Grot blasta",
        ]
        assert [child.text for child in roots[1].children] == [
            "1x Runtherd tools",
            "1x Slugga",
        ]

    def test_bullet_run_after_a_keyword_root_stays_flat(self):
        # official_3 Wazdakka Gutsmek: "Warlord" is a root, but the wargear
        # run after it must not nest beneath it — the unit is a single model.
        roots = build_tree(
            [
                "• Warlord",
                "• 1x Fixit’s wrench",
                "1x Grabba dragga",
            ]
        )

        assert [node.text for node in roots] == [
            "Warlord",
            "1x Fixit’s wrench",
            "1x Grabba dragga",
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

    def test_unbulleted_continuation_line_is_a_sibling(self):
        # official_4 Chaos Terminator Squad: app v2.6.0 (144) continues a
        # bulleted list with plain lines aligned under the first one's text.
        roots = build_tree(
            [
                "• Attached as: Bodyguard",
                "  • 1x Terminator Champion",
                "    • 1x Accursed weapon",
                "      1x Combi-bolter",
                "  • 9x Chaos Terminator",
                "    • 9x Accursed weapon",
                "      9x Combi-bolter",
            ]
        )

        # The out-dented "Attached as:" line takes no children.
        assert [node.text for node in roots] == [
            "Attached as: Bodyguard",
            "1x Terminator Champion",
            "9x Chaos Terminator",
        ]
        assert roots[0].children == []
        assert [child.text for child in roots[1].children] == [
            "1x Accursed weapon",
            "1x Combi-bolter",
        ]
        assert [child.text for child in roots[2].children] == [
            "9x Accursed weapon",
            "9x Combi-bolter",
        ]

    def test_sub_bullets_nest_under_the_bullet_above(self):
        # official_12 Ravenwing Command Squad: some v2.6.0 (3) exports write
        # every line at column zero and mark wargear with a "◦" sub-bullet.
        roots = build_tree(
            [
                "• Attached as: Support (Character)",
                "• 1x Ravenwing Champion",
                "◦ 1x Bolt pistol",
                "◦ Enhancements: Recon Hunter",
                "• 1x Ravenwing Apothecary",
                "◦ 1x Plasma talon",
            ],
            sub_bullets=True,
        )

        assert [(node.text, [c.text for c in node.children]) for node in roots] == [
            ("Attached as: Support (Character)", []),
            ("1x Ravenwing Champion", ["1x Bolt pistol", "Enhancements: Recon Hunter"]),
            ("1x Ravenwing Apothecary", ["1x Plasma talon"]),
        ]

    def test_sub_bullets_skip_a_keyword_line_to_reach_their_model(self):
        # official_11 Fabius Bile: "• Warlord" sits between the model and its
        # "◦" wargear.
        roots = build_tree(
            [
                "• 1x Fabius Bile",
                "• Warlord",
                "◦ 1x Chirurgeon",
                "◦ 1x Rod of Torment",
            ],
            sub_bullets=True,
        )

        assert [(node.text, [c.text for c in node.children]) for node in roots] == [
            ("1x Fabius Bile", ["1x Chirurgeon", "1x Rod of Torment"]),
            ("Warlord", []),
        ]

    def test_sub_bullet_export_flat_body_has_no_children(self):
        # official_12 Sammael: in a sub-bullet export a body without "◦"
        # lines is flat, last line included.
        roots = build_tree(
            [
                "• Attached as: Leader (Character)",
                "• 1x Bolt Pistol",
                "• 1x The Raven Sword",
            ],
            sub_bullets=True,
        )

        assert all(node.children == [] for node in roots)

    def test_keyword_line_ending_a_bullet_run_body_is_a_root(self):
        # official_16 Gretchin: the enhancement follows a bullet run and must
        # not be read as that run's wargear.
        roots = build_tree(
            [
                "• Attached as: Bodyguard (Battleline)",
                "• 20x Gretchin",
                "• 20x Grot Blasta",
                "20x Scavenged Shivs",
                "• Enhancement: Extra Sneaky (Upgrade)",
            ]
        )

        assert [node.text for node in roots] == [
            "Attached as: Bodyguard (Battleline)",
            "20x Gretchin",
            "Enhancement: Extra Sneaky (Upgrade)",
        ]


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

    def test_bullet_run_unit_gets_one_model_set_per_root(self):
        # official_3 Flash Gitz: a childless bulleted root (Ammo Runt) is
        # still a model set, and the enhancement is lifted from the runs.
        unit = parse_unit(
            [
                "Flash Gitz (165 points)",
                "• 1x Ammo Runt",
                "• Enhancement: Dead Shiny Shootas (Upgrade)",
                "• 1x Kaptin",
                "• 1x Choppa",
                "1x Snazzgun",
                "• 9x Flash Git",
                "• 9x Choppa",
                "9x Snazzgun",
            ],
            "OTHER DATASHEETS",
        )

        assert unit.enhancement == "Dead Shiny Shootas (Upgrade)"
        assert [(ms.name, ms.num_models, ms.wargear) for ms in unit.composition] == [
            ("Ammo Runt", 1, {}),
            ("Kaptin", 1, {"Choppa": 1, "Snazzgun": 1}),
            ("Flash Git", 9, {"Choppa": 9, "Snazzgun": 9}),
        ]

    def test_attached_as_without_parenthetical(self):
        # official_3 Gretchin: the newer dialect writes "Attached as:
        # Bodyguard" with no parenthetical at all.
        unit = parse_unit(
            [
                "Gretchin (45 points)",
                "• Attached as: Bodyguard",
                "• 10x Gretchin",
                "• 10x Grot blasta",
            ],
            "ATTACHED UNITS",
        )

        assert unit.attachment is not None
        assert unit.attachment.role == "Bodyguard"
        assert unit.attachment.role_detail == ""

    def test_count_less_body_lines_become_decorations(self):
        # official_3 Wartrakk: bare wargear names, no bullets and no "Nx".
        # They are kept as decorations rather than given fabricated counts.
        unit = parse_unit(
            [
                "Wartrakk (60 points)",
                "Choppas",
                "Kustom Shoota",
                "Rokkits",
            ],
            "OTHER DATASHEETS",
        )

        assert unit.decorations == ["Choppas", "Kustom Shoota", "Rokkits"]
        assert [(ms.name, ms.num_models, ms.wargear) for ms in unit.composition] == [
            ("Wartrakk", 1, {})
        ]

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
        # Synthetic: no fixture has one yet, but the model keeps an escape
        # hatch for body lines that are neither wargear nor a known keyword.
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

    def test_enhancement_under_a_model_set_is_lifted(self):
        # official_12 Ravenwing Command Squad
        unit = parse_unit(
            [
                "Ravenwing Command Squad (135 Points)",
                "• 1x Ravenwing Champion",
                "◦ 1x Bolt pistol",
                "◦ Enhancements: Recon Hunter",
                "• 1x Ravenwing Apothecary",
                "◦ 1x Plasma talon",
            ],
            "ATTACHED UNITS",
            sub_bullets=True,
        )

        assert unit.enhancement == "Recon Hunter"
        assert unit.decorations == []
        assert [(ms.name, ms.num_models, ms.wargear) for ms in unit.composition] == [
            ("Ravenwing Champion", 1, {"Bolt pistol": 1}),
            ("Ravenwing Apothecary", 1, {"Plasma talon": 1}),
        ]
