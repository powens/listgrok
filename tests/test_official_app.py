import json
from pathlib import Path

import pytest

from listgrok import ParseError
from listgrok.parsers.official_app import parse_official_app

EXAMPLES = Path(__file__).parents[1] / "examples" / "official_app"

OFFICIAL_EXAMPLES = {
    "official_1.txt": {
        "name": "11th stuff",
        "points": 2000,
        "super_faction": "",
        "faction": "T’au Empire",
        "detachments": ["Retaliation Cadre"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 18,
        "unit_points_total": 2000,
        "attached_groups": 4,
        "decorations": {},
    },
    "official_2.txt": {
        "name": "Awoo",
        "points": 1260,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": [
            "Champions of Fenris",
            "Legends of Saga and Song",
            "Veterans of the Fang",
        ],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 9,
        "unit_points_total": 1260,
        "attached_groups": 1,
        "decorations": {},
    },
    # The app's newer compact dialect: no army-name block (name stays "" and
    # points None), a labelled "Force Dispositions:" line, the attached-units
    # heading fused with its first group line, and unindented bullet-run unit
    # bodies. "Kult of Speed and More Dakka!" is the documented comma-free
    # limitation: it may be two detachments, but the export carries no signal.
    "official_3.txt": {
        "name": "",
        "points": None,
        "super_faction": "",
        "faction": "Orks",
        "detachments": ["Kult of Speed", "More Dakka!"],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 22,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {"Wartrakk": ["Choppas", "Kustom Shoota", "Rokkits"]},
    },
    # App v2.6.0 (144): classic headings but lower-case "points", the fused
    # "Attached Units" / "Attached Unit 1" heading, "• Attached as:" one level
    # out from the rest of the body, and unbulleted continuation lines. The
    # detachment line is the comma-free limitation again.
    "official_4.txt": {
        "name": "csm Terminators",
        "points": 2000,
        "super_faction": "",
        "faction": "Chaos Space Marines",
        "detachments": ["Cabal of Chaos", "Warpstrike Champions"],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {
            "Heretic Astartes Daemon Prince with Wings": [
                "Daemonic Allegiance: Tzeentch"
            ]
        },
    },
    # The export writes two spaces before "(2,000 Points)"; the name must not
    # keep the extra one.
    "official_5.txt": {
        "name": "I choose violence.",
        "points": 2000,
        "super_faction": "",
        "faction": "Chaos Daemons",
        "detachments": ["Cavalcade of Chaos", "Shadow Legion"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 9,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    # official_6 and official_7 have army names containing a blank line; the
    # name is kept verbatim, blank line included.
    "official_6.txt": {
        "name": "https://youtu.be/nkpFuUWOjPY?si=djM6wbdZhwjA8GsG\n\nThey did the mash",
        "points": 2000,
        "super_faction": "",
        "faction": "Drukhari",
        "detachments": ["Kabalite Cartel", "Tools of Torment"],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 18,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    "official_7.txt": {
        "name": "Round 2 list\n\nQFP",
        "points": 2000,
        "super_faction": "",
        "faction": "Imperial Knights",
        "detachments": ["Gate Warden Lance", "Questor Forgepact"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 12,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    # official_8 is official_4 re-exported from app v2.7.1, which title-cases
    # the attached-units heading and fuses it with the first group line.
    "official_8.txt": {
        "name": "csm Terminators 1.1",
        "points": 1985,
        "super_faction": "",
        "faction": "Chaos Space Marines",
        "detachments": ["Cabal of Chaos", "Warpstrike Champions"],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1985,
        "attached_groups": 3,
        "decorations": {
            "Heretic Astartes Daemon Prince with Wings": [
                "Daemonic Allegiance: Tzeentch"
            ],
        },
    },
    # Classic headings, but the unit bodies have lost their indentation (e.g.
    # in copy/paste); every line is still bulleted — "•" for a model set, "◦" for its wargear.
    "official_9.txt": {
        "name": "Suck my Guard",
        "points": 2000,
        "super_faction": "",
        "faction": "Adeptus Custodes",
        "detachments": ["Dread Host", "Honoured Companions", "Lions of the Emperor"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 10,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    # official_10 is official_5 re-exported from app v2.8.1 (1).
    "official_10.txt": {
        "name": "I choose violence.",
        "points": 2000,
        "super_faction": "",
        "faction": "Chaos Daemons",
        "detachments": ["Cavalcade of Chaos", "Shadow Legion"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 9,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
}


def parse_example(filename: str):
    return parse_official_app((EXAMPLES / filename).read_text())


# Synthetic: no 11th edition fixture has a grouped unit that omits its
# "Attached as:" line, so this input is hand-built to exercise that path —
# the fold must still stamp the group onto the unit with an empty role
# rather than leaving attachment=None.
GROUPED_UNIT_WITHOUT_ATTACHED_AS = """Test Army (100 Points)

Test Faction
Test Detachment (3 Detachment Points)
Test Disposition
Strike Force (100 Points)

ATTACHED UNITS

Attached unit 1

Test Unit (50 Points)
  • 1x Test Wargear
"""

# Synthetic: a second block carrying a "(N Detachment Points)" line, which is
# the HEADER signature. classify_blocks has no way to tell this apart from a
# legitimate header, so the fold itself must reject the second one rather than
# silently overwriting all the metadata parsed from the first.
TWO_HEADER_BLOCKS = """Test Army (100 Points)

Test Faction
Test Detachment (3 Detachment Points)
Test Disposition
Strike Force (100 Points)

Test Faction Two
Test Detachment Two (3 Detachment Points)
Test Disposition Two
Strike Force (100 Points)

CHARACTERS

Test Unit (50 Points)
  • 1x Test Wargear
"""


class TestAllOfficialExamples:
    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_metadata(self, filename):
        expected = OFFICIAL_EXAMPLES[filename]
        army_list = parse_example(filename)

        assert army_list.name == expected["name"]
        assert army_list.points == expected["points"]
        assert army_list.super_faction == expected["super_faction"]
        assert army_list.faction == expected["faction"]
        assert army_list.detachments == expected["detachments"]
        assert army_list.detachment_points == expected["detachment_points"]
        assert army_list.disposition == expected["disposition"]
        assert army_list.army_size == expected["army_size"]
        assert army_list.army_size_points == expected["army_size_points"]
        assert len(army_list.units) == expected["unit_count"]

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_units_are_well_formed(self, filename):
        expected_decorations = OFFICIAL_EXAMPLES[filename]["decorations"]
        army_list = parse_example(filename)

        for unit in army_list.units:
            assert unit.name, f"{filename}: unit with empty name"
            assert isinstance(unit.points, int)
            assert unit.sheet_type, f"{filename}: {unit.name} has no sheet type"
            assert unit.composition, f"{filename}: {unit.name} has no composition"
            # decorations is an escape hatch for body lines that are neither
            # "Nx wargear" nor a known keyword. official_3's Wartrakk shows the
            # newer dialect writing count-less wargear names, which land here
            # rather than being fabricated into counted wargear; each entry
            # tabulates them per unit name, and anything else appearing means
            # an Enhancements:/wargear match regressed rather than the fixture
            # growing a legitimately odd line.
            assert unit.decorations == expected_decorations.get(unit.name, []), (
                f"{filename}: {unit.name} has unexpected decorations"
            )
            for model_set in unit.composition:
                assert model_set.name, f"{filename}: {unit.name} model set unnamed"
                assert model_set.num_models, (
                    f"{filename}: {unit.name} model set has no num_models"
                )
                assert all(count > 0 for count in model_set.wargear.values())

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_parsed_list_is_json_serialisable(self, filename):
        army_list = parse_example(filename)

        # Every to_dict test elsewhere builds objects with empty composition,
        # so UnitComposition.to_dict() never runs there. Exercising it here,
        # over a fully parsed tree, proves the whole model is JSON-clean.
        json.dumps(army_list.to_dict())

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_unit_points_sum_to_the_list_total(self, filename):
        # The total is tabulated rather than read back from army_list.points
        # because the newer dialect (official_3) has no list-points line —
        # its points stay None while the units must still sum correctly.
        army_list = parse_example(filename)

        expected_total = OFFICIAL_EXAMPLES[filename]["unit_points_total"]
        assert sum(unit.points or 0 for unit in army_list.units) == expected_total

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_attached_units_pair_a_leader_with_a_bodyguard(self, filename):
        army_list = parse_example(filename)

        groups: dict[str, list[str]] = {}
        for unit in army_list.units:
            if unit.attachment is not None:
                groups.setdefault(unit.attachment.group, []).append(
                    unit.attachment.role
                )

        assert len(groups) == OFFICIAL_EXAMPLES[filename]["attached_groups"]
        for group, roles in groups.items():
            # Case-insensitive: the classic dialect writes "Attached unit 1",
            # the newer one "Attached Unit 1"; both are kept verbatim.
            assert group.lower().startswith("attached unit "), group
            assert sorted(roles) == ["Bodyguard", "Leader"]

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_unattached_units_have_no_attachment(self, filename):
        army_list = parse_example(filename)

        for unit in army_list.units:
            if unit.sheet_type != "ATTACHED UNITS":
                assert unit.attachment is None, unit.name


class TestOfficial1Details:
    def test_warlord_is_the_enforcer_commander(self):
        army_list = parse_example("official_1.txt")

        warlords = [unit.name for unit in army_list.units if unit.is_warlord]
        assert warlords == ["Commander in Enforcer Battlesuit"]

    def test_enhancement_is_read_from_an_attached_unit(self):
        army_list = parse_example("official_1.txt")

        enhanced = {
            unit.name: unit.enhancement for unit in army_list.units if unit.enhancement
        }
        assert enhanced == {
            "Commander in Coldstar Battlesuit": "Prototype Weapon System"
        }

    def test_character_with_two_named_models(self):
        # "The Twin Lance" is a CHARACTERS entry with two model sets.
        army_list = parse_example("official_1.txt")

        twins = next(u for u in army_list.units if u.name == "The Twin Lance")
        assert twins.sheet_type == "CHARACTERS"
        assert [model_set.name for model_set in twins.composition] == [
            "Ri’Lantar",
            "Ri’Locai",
        ]


class TestOfficial2Details:
    def test_sheet_types(self):
        army_list = parse_example("official_2.txt")

        counts: dict[str, int] = {}
        for unit in army_list.units:
            counts[unit.sheet_type] = counts.get(unit.sheet_type, 0) + 1

        assert counts == {"ATTACHED UNITS": 2, "CHARACTERS": 6, "OTHER DATASHEETS": 1}

    def test_bodyguard_carries_its_battleline_detail(self):
        army_list = parse_example("official_2.txt")

        blood_claws = next(u for u in army_list.units if u.name == "Blood Claws")
        assert blood_claws.attachment is not None
        assert blood_claws.attachment.role == "Bodyguard"
        assert blood_claws.attachment.role_detail == "Battleline"
        assert blood_claws.attachment.group == "Attached unit 1"


class TestOfficial3Details:
    # official_3.txt is the app's newer compact dialect; these tests pin the
    # behaviours that dialect introduces.

    def test_sheet_types(self):
        army_list = parse_example("official_3.txt")

        counts: dict[str, int] = {}
        for unit in army_list.units:
            counts[unit.sheet_type] = counts.get(unit.sheet_type, 0) + 1

        # "ATTACHED UNITS" proves the title-case fused heading ("Attached
        # Units") is stamped upper-cased, so consumers see one spelling.
        assert counts == {
            "ATTACHED UNITS": 4,
            "CHARACTERS": 3,
            "BATTLELINE": 3,
            "DEDICATED TRANSPORTS": 2,
            "OTHER DATASHEETS": 10,
        }

    def test_warlord_is_wazdakka(self):
        army_list = parse_example("official_3.txt")

        warlords = [unit.name for unit in army_list.units if unit.is_warlord]
        assert warlords == ["Wazdakka Gutsmek"]

    def test_enhancements_are_read_from_bullet_run_bodies(self):
        army_list = parse_example("official_3.txt")

        enhanced = [
            (unit.name, unit.enhancement)
            for unit in army_list.units
            if unit.enhancement
        ]
        assert enhanced == [
            ("Lootas", "Dead Shiny Shootas (Upgrade)"),
            ("Flash Gitz", "Dead Shiny Shootas (Upgrade)"),
            ("Flash Gitz", "Dead Shiny Shootas (Upgrade)"),
        ]

    def test_bullet_run_body_builds_model_sets(self):
        # The attached Gretchin: two bulleted roots, each followed by a
        # bullet-then-plain wargear run, with no indentation anywhere.
        army_list = parse_example("official_3.txt")

        gretchin = next(
            u
            for u in army_list.units
            if u.name == "Gretchin" and u.attachment is not None
        )
        assert [
            (ms.name, ms.num_models, ms.wargear) for ms in gretchin.composition
        ] == [
            ("Gretchin", 10, {"Close combat weapon": 10, "Grot blasta": 10}),
            ("Runtherd", 1, {"Runtherd tools": 1, "Slugga": 1}),
        ]

    def test_childless_bulleted_root_is_a_model_set(self):
        # Flash Gitz: the Ammo Runt root has no wargear run of its own.
        army_list = parse_example("official_3.txt")

        flash_gitz = next(u for u in army_list.units if u.name == "Flash Gitz")
        assert [
            (ms.name, ms.num_models, ms.wargear) for ms in flash_gitz.composition
        ] == [
            ("Ammo Runt", 1, {}),
            ("Kaptin", 1, {"Choppa": 1, "Snazzgun": 1}),
            ("Flash Git", 9, {"Choppa": 9, "Snazzgun": 9}),
        ]

    def test_count_less_wargear_lines_land_in_decorations(self):
        # Wartrakk's body is bare wargear names — no bullets, no "Nx". They
        # are kept as decorations rather than fabricated into counted wargear.
        army_list = parse_example("official_3.txt")

        wartrakk = next(u for u in army_list.units if u.name == "Wartrakk")
        assert wartrakk.decorations == ["Choppas", "Kustom Shoota", "Rokkits"]
        assert [
            (ms.name, ms.num_models, ms.wargear) for ms in wartrakk.composition
        ] == [("Wartrakk", 1, {})]

    def test_bodyguard_without_parenthetical_has_empty_detail(self):
        army_list = parse_example("official_3.txt")

        gretchin = next(
            u
            for u in army_list.units
            if u.name == "Gretchin" and u.attachment is not None
        )
        assert gretchin.attachment.role == "Bodyguard"
        assert gretchin.attachment.role_detail == ""
        assert gretchin.attachment.group == "Attached Unit 1"


class TestOfficial4Details:
    # official_4.txt is app v2.6.0 (144); these tests pin its body layout.

    def test_attached_as_line_does_not_swallow_the_body(self):
        # "• Attached as:" sits one level out from "  • Warlord" and the
        # wargear; they must not nest beneath it.
        army_list = parse_example("official_4.txt")

        kravek = next(u for u in army_list.units if u.name == "Kravek Morne")
        assert kravek.is_warlord
        assert kravek.attachment is not None
        assert kravek.attachment.role == "Leader"
        assert [(ms.name, ms.num_models, ms.wargear) for ms in kravek.composition] == [
            (
                "Kravek Morne",
                1,
                {
                    "Baleflamer": 1,
                    "Combi-bolter": 1,
                    "Last Argument and power fist": 1,
                    "Servo-harness": 1,
                },
            )
        ]

    def test_unbulleted_continuation_lines_are_wargear_of_the_model_set(self):
        army_list = parse_example("official_4.txt")

        cultists = next(u for u in army_list.units if u.name == "Cultist Mob")
        assert [
            (ms.name, ms.num_models, ms.wargear) for ms in cultists.composition
        ] == [
            ("Cultist Champion", 1, {"Autopistol": 1, "Brutal assault weapon": 1}),
            ("Chaos Cultist", 9, {"Autopistol": 9, "Brutal assault weapon": 9}),
        ]


def compositions(army_list):
    return [
        (
            unit.name,
            unit.enhancement,
            [(ms.name, ms.num_models, ms.wargear) for ms in unit.composition],
        )
        for unit in army_list.units
    ]


class TestOfficial9Details:
    # official_9.txt's unit bodies are unindented but fully bulleted.

    def test_warlord_is_trajann(self):
        army_list = parse_example("official_9.txt")

        warlords = [unit.name for unit in army_list.units if unit.is_warlord]
        assert warlords == ["Trajann Valoris"]

    def test_every_unit_has_its_wargear_under_its_model_sets(self):
        army_list = parse_example("official_9.txt")

        guard = [("Custodian Guard", 3, {"Guardian Spear": 3, "Vexilla": 1})]
        sentinels = [
            (
                "Custodian Guard",
                3,
                {"Praesidium Shield": 3, "Sentinel Blade": 3, "Vexilla": 1},
            )
        ]
        assert compositions(army_list) == [
            (
                "Trajann Valoris",
                "",
                [
                    (
                        "Trajann Valoris",
                        1,
                        {"Eagle’s Scream": 1, "Watcher’s Axe": 1},
                    )
                ],
            ),
            (
                "Allarus Custodians",
                "",
                [
                    (
                        "Allarus Custodians",
                        3,
                        {
                            "Balistus Grenade Launcher": 3,
                            "Guardian Spear": 3,
                            "Vexilla": 1,
                        },
                    )
                ],
            ),
            # The export writes a non-breaking hyphen (U+2011); it is kept.
            (
                "Shield‑Captain",
                "",
                [
                    (
                        "Shield‑Captain",
                        1,
                        {"Eternity-pattern Paragon Blade": 1, "Praesidium Shield": 1},
                    )
                ],
            ),
            (
                "Custodian Wardens",
                "",
                [("Custodian Wardens", 2, {"Guardian Spear": 2, "Vexilla": 1})],
            ),
            ("Custodian Guard Sodality", "", guard),
            ("Custodian Guard Sodality", "", guard),
            ("Sentinel Guard Sodality", "", sentinels),
            ("Sentinel Guard Sodality", "", sentinels),
            (
                "Prosecutor Squad",
                "",
                [("Prosecutors", 4, {"Boltgun": 4, "Gun Stock": 4})],
            ),
            (
                "Witchseeker Squad",
                "",
                [("Witchseekers", 4, {"Flamer": 4, "Gun Stock": 4})],
            ),
        ]


class TestOfficial10Details:
    def test_warlord_is_belakor(self):
        army_list = parse_example("official_10.txt")

        warlords = [unit.name for unit in army_list.units if unit.is_warlord]
        assert warlords == ["Be’lakor"]

    def test_every_unit_has_its_wargear_and_enhancement(self):
        army_list = parse_example("official_10.txt")

        bloodcrushers = [
            ("Bloodhunter", 1, {"Hellblade": 1, "Juggernaut’s bladed horn": 1}),
            (
                "Bloodcrusher",
                5,
                {
                    "Daemonic Icon": 1,
                    "Hellblade": 5,
                    "Instrument of Chaos": 1,
                    "Juggernaut’s bladed horn": 5,
                },
            ),
        ]
        screamers = [("Screamer", 6, {"Lamprey bite": 6})]
        assert compositions(army_list) == [
            (
                "Skullmaster",
                "Malice Made Manifest",
                [
                    (
                        "Skullmaster",
                        1,
                        {"Blade of blood": 1, "Juggernaut’s bladed horn": 1},
                    )
                ],
            ),
            ("Bloodcrushers", "", bloodcrushers),
            (
                "Be’lakor",
                "",
                [
                    (
                        "Be’lakor",
                        1,
                        {"Betraying Shades": 1, "The Blade of Shadows": 1},
                    )
                ],
            ),
            (
                "Bloodthirster",
                "Fade to Darkness",
                [
                    (
                        "Bloodthirster",
                        1,
                        {"Great axe of Khorne": 1, "Hellfire breath": 1},
                    )
                ],
            ),
            (
                "Lord of Change",
                "",
                [
                    (
                        "Lord of Change",
                        1,
                        {
                            "Bolt of Change": 1,
                            "Rod of sorcery": 1,
                            "Staff of Tzeentch": 1,
                        },
                    )
                ],
            ),
            ("Bloodcrushers", "", bloodcrushers),
            ("Screamers", "", screamers),
            ("Screamers", "", screamers),
            (
                "Chaos Lord in Terminator Armour",
                "",
                [
                    (
                        "Chaos Lord in Terminator Armour",
                        1,
                        {"Combi-weapon": 1, "Power fist": 1},
                    )
                ],
            ),
        ]


class TestGroupAttachmentFold:
    def test_unit_with_no_attached_as_line_is_still_stamped_with_its_group(self):
        army_list = parse_official_app(GROUPED_UNIT_WITHOUT_ATTACHED_AS)

        unit = army_list.units[0]
        assert unit.attachment is not None
        assert unit.attachment.group == "Attached unit 1"
        assert unit.attachment.role == ""
        assert unit.attachment.role_detail == ""


class TestDuplicateHeaderFold:
    def test_second_header_block_raises_instead_of_overwriting_metadata(self):
        with pytest.raises(ParseError):
            parse_official_app(TWO_HEADER_BLOCKS)
