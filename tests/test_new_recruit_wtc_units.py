import pytest

from listgrok import ParseError
from listgrok.parsers.new_recruit_wtc.units import is_unit_header, parse_unit


def model_sets(unit):
    return [(ms.name, ms.num_models, ms.wargear) for ms in unit.composition]


class TestIsUnitHeader:
    @pytest.mark.parametrize(
        "line",
        [
            "Char1: 1x Valerian (110 pts): Warlord, Gnosis",  # nr_wtc_0
            "5x Custodian Wardens (250 pts)",  # nr_wtc_0
            "1x Land Raider (220 pts)",  # nr_wtc_9
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

    def test_unknown_body_line_is_a_decoration(self):
        unit, _ = parse_unit("1x Land Raider (220 pts)", ["Some note"])

        assert unit.decorations == ["Some note"]

    def test_unparseable_header_raises(self):
        with pytest.raises(ParseError, match="Unparseable unit header"):
            parse_unit("Land Raider (220 pts)", [])
