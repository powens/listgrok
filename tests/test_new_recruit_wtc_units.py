import pytest

from listgrok import ParseError
from listgrok.parsers.new_recruit_wtc.units import (
    is_body_line,
    is_unit_header,
    parse_unit,
)


def model_sets(unit):
    return [(ms.name, ms.num_models, ms.wargear) for ms in unit.composition]


class TestIsUnitHeader:
    @pytest.mark.parametrize(
        "line",
        [
            "Char1: 1x Valerian (110 pts): Warlord, Gnosis",  # nr_wtc_0
            "5x Custodian Wardens (250 pts)",  # nr_wtc_0
            "1x Land Raider (220 pts)",  # nr_wtc_9
            # Not in a fixture (from review): nr_wtc_10's ENHANCEMENT line
            # uses a `Moun5:` label, so any such label may prefix a unit.
            "Moun5: 6x Bloodcrushers (220 pts)",
        ],
    )
    def test_unit_headers(self, line):
        assert is_unit_header(line)

    @pytest.mark.parametrize(
        "line",
        [
            "• 4x Custodian Warden (Guardian Spear): 4 with Guardian Spear",
            "  Attached to Valerian",
            "Enhancement: Superior Creation (+25 pts)",
            "    6 with Autopistol, Chainblade, Close combat weapon",
        ],
    )
    def test_body_lines(self, line):
        assert not is_unit_header(line)


class TestIsBodyLine:
    @pytest.mark.parametrize(
        "line",
        [
            "Enhancement: Brazenmaw (+15 pts)",  # nr_wtc_10
            "• 5x Bloodcrusher",  # nr_wtc_10
            "3 with Hellblade, Juggernaut's bladed horn",  # nr_wtc_10
            "  Attached to Valerian",  # nr_wtc_0
            "Leading Custodian Wardens",  # nr_wtc_0
            "Char2: 1x Blade Champion (135 pts): Vaultswords",  # nr_wtc_0
        ],
    )
    def test_body_lines(self, line):
        assert is_body_line(line)

    @pytest.mark.parametrize(
        "line", ["Thanks, what do you think?", "```", "2 Storm Bolters"]
    )
    def test_commentary(self, line):
        assert not is_body_line(line)


class TestParseUnit:
    def test_character_with_inline_wargear_and_warlord(self):
        # nr_wtc_0 Valerian
        unit, links = parse_unit(
            "Char1: 1x Valerian (110 pts): Warlord, Gnosis",
            ["Leading Custodian Wardens"],
        )

        assert unit.name == "Valerian"
        assert unit.points == 110
        assert unit.is_warlord
        assert model_sets(unit) == [("Valerian", 1, {"Gnosis": 1})]
        assert links.leading == ["Custodian Wardens"]
        assert links.attached_to == []

    def test_enhancement_is_read_without_its_points(self):
        # nr_wtc_0 Blade Champion
        unit, _ = parse_unit(
            "Char2: 1x Blade Champion (135 pts): Vaultswords",
            ["Enhancement: Superior Creation (+25 pts)", "Leading Custodian Guard"],
        )

        assert unit.enhancement == "Superior Creation"
        assert not unit.is_warlord

    def test_inline_with_item_multiplies_every_weapon(self):
        # nr_wtc_0 Allarus Custodians
        unit, _ = parse_unit(
            "6x Allarus Custodians (340 pts): 6 with Balistus grenade launcher, "
            "Guardian Spear",
            [],
        )

        assert model_sets(unit) == [
            (
                "Allarus Custodians",
                6,
                {"Balistus grenade launcher": 6, "Guardian Spear": 6},
            )
        ]

    def test_with_item_after_other_items_owns_the_rest(self):
        # Not in a fixture (from review): a `with` clause after a leading item
        # still covers every weapon after it.
        unit, _ = parse_unit("Char1: 2x Foo (100 pts): Warlord, 2 with A, B", [])

        assert unit.is_warlord
        assert model_sets(unit) == [("Foo", 2, {"A": 2, "B": 2})]

    def test_two_with_items_on_the_header_line_stay_separate(self):
        # Not in a fixture (from review): each `K with` item starts its own group.
        unit, _ = parse_unit(
            "2x Vertus Praetors (145 pts): 1 with Interceptor lance, B, "
            "1 with Salvo launcher",
            [],
        )

        assert model_sets(unit) == [
            (
                "Vertus Praetors",
                2,
                {"Interceptor lance": 1, "B": 1, "Salvo launcher": 1},
            )
        ]

    def test_two_with_groups_on_one_body_line_stay_separate(self):
        # Not in a fixture (from review).
        unit, _ = parse_unit("2x Foo (100 pts)", ["1 with A, 1 with B"])

        assert model_sets(unit) == [("Foo", 2, {"A": 1, "B": 1})]

    def test_with_line_before_a_bullet_raises(self):
        # Not in a fixture (from review): the implicit model set already
        # claims every model, so a later bullet would count models twice.
        with pytest.raises(ParseError, match="before a model bullet"):
            parse_unit("1x Squad (100 pts)", ["5 with Bolter", "• 4x Marine"])

    def test_counted_and_repeated_inline_items(self):
        # nr_wtc_3 Defiler: "2x" counts, and a repeated name sums.
        unit, _ = parse_unit(
            "1x Defiler (330 pts): Ectoplasma destructor, 2x Excruciator cannon, "
            "Heavy reaper autocannon, Heavy reaper autocannon, Shearing claws",
            [],
        )

        assert model_sets(unit) == [
            (
                "Defiler",
                1,
                {
                    "Ectoplasma destructor": 1,
                    "Excruciator cannon": 2,
                    "Heavy reaper autocannon": 2,
                    "Shearing claws": 1,
                },
            )
        ]

    def test_bullets_and_indented_with_lines_build_model_sets(self):
        # nr_wtc_2 Goremongers
        unit, links = parse_unit(
            "8x Goremongers (75 pts)",
            [
                "• 7x Goremonger",
                "    6 with Autopistol, Chainblade, Close combat weapon",
                "    1 with Autopistol, Blood harpoon, Close combat weapon",
                "• 1x Blood Herald: Autopistol, Chainblade, Close combat weapon",
            ],
        )

        assert model_sets(unit) == [
            (
                "Goremonger",
                7,
                {
                    "Autopistol": 7,
                    "Chainblade": 6,
                    "Close combat weapon": 7,
                    "Blood harpoon": 1,
                },
            ),
            (
                "Blood Herald",
                1,
                {"Autopistol": 1, "Chainblade": 1, "Close combat weapon": 1},
            ),
        ]
        assert links.attached_to == []

    def test_bodyguard_link_keeps_its_index(self):
        # nr_wtc_2 Eightbound
        unit, links = parse_unit(
            "6x Eightbound (255 pts)",
            [
                "• 1x Eightbound Champion: Chainblades",
                "• 5x Eightbound: 5 with Chainblades",
                "  Attached to Slaughterbound[3]",
            ],
        )

        assert links.attached_to == ["Slaughterbound[3]"]
        assert model_sets(unit) == [
            ("Eightbound Champion", 1, {"Chainblades": 1}),
            ("Eightbound", 5, {"Chainblades": 5}),
        ]

    def test_bulleted_character_with_indented_leading_line(self):
        # nr_wtc_9 Chaplain Grimaldus: bullets with no wargear, the inline
        # Warlord lifted out, and the Leading line indented under the bullets.
        unit, links = parse_unit(
            "Char1: 4x Chaplain Grimaldus (100 pts): Warlord",
            [
                "• 3x Cenobyte Servitor",
                "• 1x Chaplain Grimaldus",
                "  Leading Crusader Squad",
            ],
        )

        assert unit.is_warlord
        assert model_sets(unit) == [
            ("Cenobyte Servitor", 3, {}),
            ("Chaplain Grimaldus", 1, {}),
        ]
        assert links.leading == ["Crusader Squad"]

    def test_indented_enhancement_and_with_line_without_bullets(self):
        # nr_wtc_3 Flawless Blades
        unit, _ = parse_unit(
            "6x Flawless Blades (205 pts)",
            [
                "  Enhancement: Beguiling Grotesquerie (+15 pts)",
                "  6 with Blissblade, Bolt pistol",
            ],
        )

        assert unit.enhancement == "Beguiling Grotesquerie"
        assert model_sets(unit) == [
            ("Flawless Blades", 6, {"Blissblade": 6, "Bolt pistol": 6})
        ]

    def test_unit_with_no_wargear_gets_an_empty_model_set(self):
        # nr_wtc_9 Land Raider
        unit, _ = parse_unit("1x Land Raider (220 pts)", [])

        assert model_sets(unit) == [("Land Raider", 1, {})]

    def test_count_less_numeric_item_is_a_decoration(self):
        # nr_wtc_9 Gladiator Lancer: "2 Storm Bolters" has neither "x" nor "with".
        unit, _ = parse_unit("1x Gladiator Lancer (160 pts): 2 Storm Bolters", [])

        assert unit.decorations == ["2 Storm Bolters"]
        assert model_sets(unit) == [("Gladiator Lancer", 1, {})]

    def test_counted_item_inside_with_multiplies(self):
        # Not in a fixture (from review): two claws each on four models.
        unit, _ = parse_unit(
            "4x Terminators (170 pts)",
            ["• 4x Terminator: 4 with 2x Lightning claws, Storm shield"],
        )

        assert model_sets(unit) == [
            ("Terminator", 4, {"Lightning claws": 8, "Storm shield": 4})
        ]

    def test_header_items_go_to_the_bullet_named_after_the_unit(self):
        # Not in a fixture (from review): not simply the first bullet.
        unit, _ = parse_unit(
            "Char1: 3x Leader (100 pts): Warlord, Relic blade",
            ["• 2x Servitor", "• 1x Leader"],
        )

        assert unit.is_warlord
        assert model_sets(unit) == [
            ("Servitor", 2, {}),
            ("Leader", 1, {"Relic blade": 1}),
        ]

    def test_header_items_with_no_matching_bullet_are_decorations(self):
        # Not in a fixture (from review): no bullet to credit them to.
        unit, _ = parse_unit(
            "3x Squad (100 pts): Relic blade", ["• 2x Servitor", "• 1x Sergeant"]
        )

        assert unit.decorations == ["Relic blade"]
        assert model_sets(unit) == [("Servitor", 2, {}), ("Sergeant", 1, {})]

    @pytest.mark.parametrize(
        "body",
        [["• 1x Sergeant: Warlord, Storm bolter"], ["1 with Warlord, Storm bolter"]],
    )
    def test_warlord_in_the_body_marks_the_unit(self, body):
        # Not in a fixture (from review): Warlord on a bullet or `with` line.
        unit, _ = parse_unit("1x Sergeant (20 pts)", body)

        assert unit.is_warlord
        assert model_sets(unit) == [("Sergeant", 1, {"Storm bolter": 1})]

    def test_second_enhancement_is_a_decoration(self):
        # Not in a fixture (from review): the first is kept, the second shown.
        unit, _ = parse_unit(
            "1x Captain (100 pts)",
            ["Enhancement: First (+10 pts)", "Enhancement: Second (+20 pts)"],
        )

        assert unit.enhancement == "First"
        assert unit.decorations == ["Enhancement: Second (+20 pts)"]

    def test_comma_inside_parentheses_does_not_split_an_item(self):
        # Not in a fixture (from review).
        unit, _ = parse_unit(
            "1x Captain (100 pts): Bolt pistol (Master-crafted, Relic), Sword", []
        )

        assert model_sets(unit) == [
            ("Captain", 1, {"Bolt pistol (Master-crafted, Relic)": 1, "Sword": 1})
        ]

    def test_unknown_body_line_is_a_decoration(self):
        unit, _ = parse_unit("1x Land Raider (220 pts)", ["Some note"])

        assert unit.decorations == ["Some note"]

    def test_unparseable_header_raises(self):
        with pytest.raises(ParseError, match="Unparseable unit header"):
            parse_unit("Land Raider (220 pts)", [])
