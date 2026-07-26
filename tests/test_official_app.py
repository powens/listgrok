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
        "detachments": ["Kult of Speed and More Dakka!"],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 22,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {"Wartrakk": ["Choppas", "Kustom Shoota", "Rokkits"]},
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
