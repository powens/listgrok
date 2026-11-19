import json
from pathlib import Path

import pytest

from listgrok import ParseError
from listgrok.parsers.official_app import parse_official_app

EXAMPLES = Path(__file__).parents[1] / "examples" / "official_app"

OFFICIAL_EXAMPLES = {
    # official_11 and official_25 nest "Warlord" / "Enhancements:" under the
    # model that carries it rather than at the top of the body.
    "official_11.txt": {
        "name": "BLOW ME (away)",
        "points": 2000,
        "super_faction": "",
        "faction": "Astra Militarum",
        "detachments": ["Bridgehead Strike", "Combined Arms"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_12.txt": {
        "name": "Beast Slayer Again",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": [
            "Assault Brethren",
            "Saga of the Beastslayer",
            "Terminator Storm Force",
        ],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_13.txt": {
        "name": "Deathwatch 2k Voidfire",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Deathwatch",
        "detachments": ["Black Spear Task Force"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 12,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_14.txt": {
        "name": "Fuck it we Baal",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Blood Angels",
        "detachments": [
            "Assault Brethren",
            "Ironclad Champions",
            "Wrath of the Doomed",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1995,
        "attached_groups": 3,
        "decorations": {},
    },
    # official_15: an "Attached unit 1" group under CHARACTERS (no ATTACHED UNITS
    # section), and "Mark of Chaos: <god>" body lines, which land in
    # decorations. The two Chosen differ in mark, hence the points-qualified keys.
    "official_15.txt": {
        "name": "Host of Urlakh",
        "points": 2000,
        "super_faction": "",
        "faction": "Chaos Space Marines",
        "detachments": ["Pactbound Zealots"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 15,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {
            "Chaos Lord": ["Mark of Chaos: Khorne"],
            "Chosen (140)": ["Mark of Chaos: Khorne"],
            "Cultist Mob": ["Mark of Chaos: Khorne"],
            "Chaos Predator Destructor": ["Mark of Chaos: Tzeentch"],
            "Chosen (280)": ["Mark of Chaos: Slaanesh"],
            "Defiler": ["Mark of Chaos: Nurgle"],
            "Havocs": ["Mark of Chaos: Tzeentch"],
            "Helbrute": ["Mark of Chaos: Slaanesh"],
            "Raptors": ["Mark of Chaos: Khorne"],
            "Traitor Guardsmen Squad": ["Mark of Chaos: Tzeentch"],
        },
    },
    "official_16.txt": {
        "name": "Admech CyberErad T&H",
        "points": 2000,
        "super_faction": "",
        "faction": "Adeptus Mechanicus",
        "detachments": ["Cohort Cybernetica", "Eradication Cohort"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 15,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    "official_17.txt": {
        "name": "ShamblePoP",
        "points": 2000,
        "super_faction": "",
        "faction": "Death Guard",
        "detachments": ["Paragons of Putrescence", "Shamblerot Vectorium"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 2000,
        "attached_groups": 1,
        "decorations": {},
    },
    "official_18.txt": {
        "name": "Fathers of the fang",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": [
            "Assault Brethren",
            "Ironstorm Spearhead",
            "Saga of the Beastslayer",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_19.txt": {
        "name": "sister.",
        "points": 2000,
        "super_faction": "",
        "faction": "Adepta Sororitas",
        "detachments": ["Bringers of Flame", "Sacred Champions"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 16,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    "official_20.txt": {
        "name": "11/15/26 BA 18SG Lmao",
        "points": 1995,
        "super_faction": "Space Marines",
        "faction": "Blood Angels",
        "detachments": ["Assault Brethren", "Encarmine Speartip", "Ironclad Champions"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 12,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_21.txt": {
        "name": "Need to gaârd something over there v1",
        "points": 2000,
        "super_faction": "",
        "faction": "Leagues of Votann",
        "detachments": ["Farseekers", "Needgaârd Oathband"],
        "detachment_points": 3,
        "disposition": "Reconnaissance",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_22.txt": {
        "name": "Iron Supplements",
        "points": 1995,
        "super_faction": "",
        "faction": "Chaos Space Marines",
        "detachments": ["Cabal of Chaos", "Warpstrike Champions"],
        "detachment_points": 3,
        "disposition": "Disruption",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1995,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_23.txt": {
        "name": "I'm going to make so many friends this weekend.",
        "points": 1990,
        "super_faction": "",
        "faction": "Necrons",
        "detachments": ["Awakened Dynasty"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 16,
        "unit_points_total": 1990,
        "attached_groups": 4,
        "decorations": {},
    },
    "official_24.txt": {
        "name": "WAAAAAAGGGHHH",
        "points": 1995,
        "super_faction": "",
        "faction": "Orks",
        "detachments": ["Dread Mob", "Green Tide", "Taktikal Brigade"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 1995,
        "attached_groups": 4,
        "decorations": {},
    },
    "official_25.txt": {
        "name": "Sons of dom",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Black Templars",
        "detachments": [
            "Assault Brethren",
            "Ironstorm Spearhead",
            "Tacticus Attack Force",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 17,
        "unit_points_total": 2000,
        "attached_groups": 2,
        "decorations": {},
    },
    # official_26: "<Detachment> Keywords: Character" body lines land in decorations.
    "official_26.txt": {
        "name": "I have no idea what i’m doing… but can you kill this?",
        "points": 1990,
        "super_faction": "",
        "faction": "Astra Militarum",
        "detachments": ["Abhuman Auxiliaries", "Steel Hammer"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 13,
        "unit_points_total": 1990,
        "attached_groups": 0,
        "decorations": {
            "Baneblade": ["Steel Hammer Keywords: Character"],
            "Doomhammer": ["Steel Hammer Keywords: Character"],
        },
    },
    "official_27.txt": {
        "name": "his is my parameter, and my parameter is me",
        "points": 2000,
        "super_faction": "Space Marines",
        "faction": "Dark Angels",
        "detachments": [
            "Assault Brethren",
            "Stormlance Task Force",
            "Terminator Storm Force",
        ],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 2000,
        "attached_groups": 3,
        "decorations": {},
    },
    # official_28: the army name carries no "(N Points)" suffix, so points
    # stays None; everything before the header is the name.
    "official_28.txt": {
        "name": "No more Overwatch…our dreams lie dead….",
        "points": None,
        "super_faction": "",
        "faction": "Imperial Knights",
        "detachments": ["Questor Forgepact", "Valourstrike Lance"],
        "detachment_points": 3,
        "disposition": "Purge the Foe",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 10,
        "unit_points_total": 1995,
        "attached_groups": 1,
        "decorations": {},
    },
    "official_29.txt": {
        "name": "Space wolves",
        "points": 1975,
        "super_faction": "Space Marines",
        "faction": "Space Wolves",
        "detachments": ["Saga of the Great Wolf", "Terminator Storm Force"],
        "detachment_points": 3,
        "disposition": "Take and Hold",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 10,
        "unit_points_total": 1975,
        "attached_groups": 2,
        "decorations": {},
    },
    "official_30.txt": {
        "name": "worlds",
        "points": 1995,
        "super_faction": "",
        "faction": "Tyranids",
        "detachments": ["Assimilation Swarm", "Talons of the Norn Queen"],
        "detachment_points": 3,
        "disposition": "Priority Assets",
        "army_size": "Strike Force",
        "army_size_points": 2000,
        "unit_count": 14,
        "unit_points_total": 1995,
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
            # "Nx wargear" nor a known keyword ("Mark of Chaos: Khorne" in
            # official_15); each entry tabulates them per unit name, and
            # anything else appearing means an Enhancements:/wargear match
            # regressed rather than the fixture growing a legitimately odd line.
            # A "Name (points)" key wins over a plain "Name" one, for a list
            # whose same-named units decorate differently (official_15).
            expected = expected_decorations.get(
                f"{unit.name} ({unit.points})",
                expected_decorations.get(unit.name, []),
            )
            assert unit.decorations == expected, (
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
        # because a list may have no list-points line (official_28, and the
        # compact dialect) — its points stay None while the units must still
        # sum correctly.
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
            if not any(roles):
                # official_15 writes the group with no "Attached as:" lines.
                continue
            # One bodyguard unit, and one or more characters joining it: a
            # group can hold two Leaders (official_11) or a Support character
            # alongside or instead of a Leader (official_12, official_19).
            assert roles.count("Bodyguard") == 1, (group, roles)
            others = [role for role in roles if role != "Bodyguard"]
            assert others, (group, roles)
            assert set(others) <= {"Leader", "Support"}, (group, roles)

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_attachment_comes_only_from_a_group_heading(self, filename):
        army_list = parse_example(filename)

        for unit in army_list.units:
            # official_15 puts its group heading under CHARACTERS rather than
            # an ATTACHED UNITS section, so the sheet type alone does not say
            # whether a unit is attached; only a group heading above it does.
            if unit.sheet_type == "ATTACHED UNITS":
                assert unit.attachment is not None, unit.name
            if unit.attachment is not None:
                assert unit.attachment.group, unit.name


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


ARMY_NAME_HEADER = """Imperial Knights
Questor Forgepact (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

CHARACTERS

Knight Crusader (410 Points)
  • 1x Avenger gatling cannon
"""


class TestArmyNameFold:
    def test_name_without_a_points_suffix_has_no_points(self):
        # official_28
        army_list = parse_official_app(
            "No more Overwatch…our dreams lie dead….\n\n" + ARMY_NAME_HEADER
        )

        assert army_list.name == "No more Overwatch…our dreams lie dead…."
        assert army_list.points is None

    def test_points_suffix_is_read_off_the_end_of_the_name(self):
        army_list = parse_official_app(
            "Round 2 list\n\nQFP (2,000 Points)\n\n" + ARMY_NAME_HEADER
        )

        assert army_list.name == "Round 2 list\n\nQFP"
        assert army_list.points == 2000

    def test_notes_after_the_points_line_are_dropped(self):
        # lvo2026_grey_knights: player notes follow the name in the same block.
        army_list = parse_official_app(
            "Palworld2 (2,000 Points)\nDonovan Sailo\nMaking Saves\n\n"
            + ARMY_NAME_HEADER
        )

        assert army_list.name == "Palworld2"
        assert army_list.points == 2000

    def test_notes_blocks_after_the_points_line_are_dropped(self):
        # lvo2026_chaos_space_marines: notes in their own blocks after the name.
        army_list = parse_official_app(
            "Snorting lines (2,000 Points)\n\nDan this is whimsy\n\n"
            "**THING YOU SHOULD KNOW***\n- a note\n\n" + ARMY_NAME_HEADER
        )

        assert army_list.name == "Snorting lines"
        assert army_list.points == 2000

    def test_without_a_points_line_only_the_first_block_is_the_name(self):
        army_list = parse_official_app(
            "No more Overwatch\n\nsome notes\nmore notes\n\n" + ARMY_NAME_HEADER
        )

        assert army_list.name == "No more Overwatch"
        assert army_list.points is None
