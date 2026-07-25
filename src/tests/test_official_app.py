from pathlib import Path

import pytest

from listgrok.parsers.official_app import parse_official_app

EXAMPLES = Path(__file__).parents[2] / "examples" / "official_app"

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
        "attached_groups": 4,
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
        "attached_groups": 1,
    },
}


def parse_example(filename: str):
    return parse_official_app((EXAMPLES / filename).read_text())


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
        army_list = parse_example(filename)

        for unit in army_list.units:
            assert unit.name, f"{filename}: unit with empty name"
            assert isinstance(unit.points, int)
            assert unit.sheet_type, f"{filename}: {unit.name} has no sheet type"
            assert unit.composition, f"{filename}: {unit.name} has no composition"
            for model_set in unit.composition:
                assert model_set.name, f"{filename}: {unit.name} model set unnamed"
                assert all(count > 0 for count in model_set.wargear.values())

    @pytest.mark.parametrize("filename", sorted(OFFICIAL_EXAMPLES))
    def test_unit_points_sum_to_the_list_total(self, filename):
        army_list = parse_example(filename)

        assert sum(unit.points or 0 for unit in army_list.units) == army_list.points

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
            assert group.startswith("Attached unit "), group
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
