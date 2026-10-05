import json
from pathlib import Path

import pytest

from listgrok import ParseError
from listgrok.parsers.new_recruit_wtc import parse_new_recruit_wtc
from listgrok.parsers.new_recruit_wtc.units import is_unit_header

EXAMPLES = Path(__file__).parents[1] / "examples" / "new_recruit" / "wtc"

WTC_EXAMPLES = {
    "nr_wtc_0.txt": {
        "points": 1990,
        "super_faction": "Imperium",
        "faction": "Adeptus Custodes",
        "detachments": ["Lions of the Emperor"],
        "disposition": "Take and Hold",
        "unit_count": 12,
        "attached_groups": 2,
        "warlord": "Valerian",
        "decorations": {},
    },
    "nr_wtc_1.txt": {
        "points": 2000,
        "super_faction": "Chaos",
        "faction": "World Eaters",
        "detachments": ["Berzerker Warband"],
        "disposition": "Purge the Foe",
        "unit_count": 17,
        "attached_groups": 4,
        "warlord": "Khârn the Betrayer",
        "decorations": {},
    },
    "nr_wtc_2.txt": {
        "points": 2000,
        "super_faction": "Chaos",
        "faction": "World Eaters",
        "detachments": ["Possessed Slaughterband", "Vessels of Wrath"],
        "disposition": "Purge the Foe",
        "unit_count": 13,
        "attached_groups": 3,
        "warlord": "Daemon Prince of Khorne",
        "decorations": {},
    },
    "nr_wtc_3.txt": {
        "points": 1990,
        "super_faction": "Chaos",
        "faction": "Emperor's Children",
        "detachments": ["Court of the Phoenician", "Spectacle of Slaughter"],
        "disposition": "Purge the Foe",
        "unit_count": 15,
        "attached_groups": 0,
        "warlord": "Lucius the Eternal",
        "decorations": {},
    },
    # "Throne‑bonded" keeps New Recruit's U+2011 non-breaking hyphen: it is
    # part of the name, unlike the U+00A0 spaces, which are normalised.
    "nr_wtc_4.txt": {
        "points": 2000,
        "super_faction": "Imperium",
        "faction": "Imperial Knights",
        "detachments": ["Throne‑bonded Outriders", "Valourstrike Lance"],
        "disposition": "Purge the Foe",
        "unit_count": 8,
        "attached_groups": 0,
        "warlord": "Cerastus Knight Lancer",
        "decorations": {},
    },
    "nr_wtc_5.txt": {
        "points": 995,
        "super_faction": "Xenos",
        "faction": "Orks",
        "detachments": ["Dread Mob", "Green Tide"],
        "disposition": "Purge the Foe",
        "unit_count": 10,
        "attached_groups": 0,
        "warlord": "Warboss in Mega Armour",
        "decorations": {},
    },
    "nr_wtc_6.txt": {
        "points": 1995,
        "super_faction": "Xenos",
        "faction": "Tyranids",
        "detachments": ["Assimilation Swarm", "Warrior Bioform Onslaught"],
        "disposition": "Priority Assets",
        "unit_count": 18,
        "attached_groups": 4,
        "warlord": "The Swarmlord",
        "decorations": {},
    },
    "nr_wtc_7.txt": {
        "points": 2000,
        "super_faction": "Imperium",
        "faction": "Imperial Knights",
        "detachments": ["Freeblade Company"],
        "disposition": "Priority Assets",
        "unit_count": 8,
        "attached_groups": 0,
        "warlord": "Knight Castellan",
        "decorations": {},
    },
    # A blank line after every unit: WTC blank lines carry no meaning.
    "nr_wtc_8.txt": {
        "points": 2000,
        "super_faction": "Imperium",
        "faction": "Imperial Knights",
        "detachments": ["Freeblade Company"],
        "disposition": "Priority Assets",
        "unit_count": 8,
        "attached_groups": 0,
        "warlord": "Knight Castellan",
        "decorations": {},
    },
    "nr_wtc_9.txt": {
        "points": 990,
        "super_faction": "Imperium",
        "faction": "Black Templars",
        "detachments": ["Gladius Task Force"],
        "disposition": "Priority Assets",
        "unit_count": 8,
        "attached_groups": 2,
        "warlord": "Chaplain Grimaldus",
        "decorations": {"Gladiator Lancer": ["2 Storm Bolters"]},
    },
}


def parse_example(filename: str):
    return parse_new_recruit_wtc((EXAMPLES / filename).read_text())


def test_every_fixture_is_listed():
    assert sorted(p.name for p in EXAMPLES.glob("*.txt")) == sorted(WTC_EXAMPLES)


class TestAllWTCExamples:
    @pytest.mark.parametrize("filename", sorted(WTC_EXAMPLES))
    def test_metadata(self, filename):
        expected = WTC_EXAMPLES[filename]
        army_list = parse_example(filename)

        assert army_list.name == ""
        assert army_list.points == expected["points"]
        assert army_list.super_faction == expected["super_faction"]
        assert army_list.faction == expected["faction"]
        assert army_list.detachments == expected["detachments"]
        assert army_list.disposition == expected["disposition"]
        assert len(army_list.units) == expected["unit_count"]

    @pytest.mark.parametrize("filename", sorted(WTC_EXAMPLES))
    def test_units_are_well_formed(self, filename):
        expected_decorations = WTC_EXAMPLES[filename]["decorations"]
        army_list = parse_example(filename)

        for unit in army_list.units:
            assert unit.name, f"{filename}: unit with empty name"
            assert isinstance(unit.points, int)
            assert unit.sheet_type == ""
            assert unit.composition, f"{filename}: {unit.name} has no composition"
            assert unit.decorations == expected_decorations.get(unit.name, []), (
                f"{filename}: {unit.name} has unexpected decorations"
            )
            for model_set in unit.composition:
                assert model_set.name, f"{filename}: {unit.name} model set unnamed"
                assert model_set.num_models, (
                    f"{filename}: {unit.name} model set has no num_models"
                )
                assert all(count > 0 for count in model_set.wargear.values())

    @pytest.mark.parametrize("filename", sorted(WTC_EXAMPLES))
    def test_unit_points_sum_to_the_list_total(self, filename):
        # Unlike official_app, WTC unit points include enhancements and always
        # sum to TOTAL ARMY POINTS, so the parsed total is the expectation.
        army_list = parse_example(filename)

        assert sum(unit.points or 0 for unit in army_list.units) == army_list.points

    @pytest.mark.parametrize("filename", sorted(WTC_EXAMPLES))
    def test_exactly_one_warlord(self, filename):
        army_list = parse_example(filename)

        warlords = [unit.name for unit in army_list.units if unit.is_warlord]
        assert warlords == [WTC_EXAMPLES[filename]["warlord"]]

    @pytest.mark.parametrize("filename", sorted(WTC_EXAMPLES))
    def test_attached_units_pair_leaders_with_one_bodyguard(self, filename):
        army_list = parse_example(filename)

        groups: dict[str, list[str]] = {}
        for unit in army_list.units:
            if unit.attachment is not None:
                assert unit.attachment.role_detail == ""
                groups.setdefault(unit.attachment.group, []).append(
                    unit.attachment.role
                )

        assert len(groups) == WTC_EXAMPLES[filename]["attached_groups"]
        assert sorted(groups) == [
            f"Attached unit {n}" for n in range(1, len(groups) + 1)
        ]
        for roles in groups.values():
            assert roles.count("Bodyguard") == 1
            assert roles.count("Leader") >= 1

    @pytest.mark.parametrize("filename", sorted(WTC_EXAMPLES))
    def test_parsed_list_is_json_serialisable(self, filename):
        json.dumps(parse_example(filename).to_dict())


class TestAttachmentPairing:
    def test_indexed_references_pick_the_nth_unit_of_that_name(self):
        # nr_wtc_2: Char2 (Slaughterbound #1) leads Eightbound[2], Char4
        # (Slaughterbound #3) leads Eightbound[1]. Groups number by bodyguard.
        army_list = parse_example("nr_wtc_2.txt")

        pairs = [
            (unit.name, unit.points, unit.attachment.group, unit.attachment.role)
            for unit in army_list.units
            if unit.attachment is not None
        ]
        assert pairs == [
            ("Slaughterbound", 100, "Attached unit 2", "Leader"),
            ("Slaughterbound", 120, "Attached unit 3", "Leader"),
            ("Slaughterbound", 100, "Attached unit 1", "Leader"),
            ("Eightbound", 255, "Attached unit 1", "Bodyguard"),
            ("Eightbound", 255, "Attached unit 2", "Bodyguard"),
            ("Exalted Eightbound", 265, "Attached unit 3", "Bodyguard"),
        ]

    def test_two_leaders_on_one_bodyguard_share_a_group(self):
        army_list = parse_new_recruit_wtc(
            make_list(
                "Char1: 1x Captain (80 pts): Warlord",
                "Leading Intercessors",
                "Char2: 1x Lieutenant (65 pts)",
                "Leading Intercessors",
                "5x Intercessors (80 pts)",
            )
        )

        assert [
            (u.name, u.attachment.group, u.attachment.role)
            for u in army_list.units
            if u.attachment is not None
        ] == [
            ("Captain", "Attached unit 1", "Leader"),
            ("Lieutenant", "Attached unit 1", "Leader"),
            ("Intercessors", "Attached unit 1", "Bodyguard"),
        ]

    def test_one_side_alone_makes_the_link(self):
        # nr_wtc_0's Custodian Guard line alone, with no Leading line.
        army_list = parse_new_recruit_wtc(
            make_list(
                "Char1: 1x Blade Champion (110 pts): Warlord, Vaultswords",
                "5x Custodian Guard (215 pts): 5 with Guardian Spear",
                "  Attached to Blade Champion",
            )
        )

        assert [u.attachment.role for u in army_list.units if u.attachment] == [
            "Leader",
            "Bodyguard",
        ]

    def test_unknown_reference_raises(self):
        with pytest.raises(ParseError, match="Unresolvable attachment reference"):
            parse_new_recruit_wtc(
                make_list(
                    "Char1: 1x Captain (80 pts): Warlord",
                    "Leading Hellblasters",
                    "5x Intercessors (80 pts)",
                )
            )

    def test_ambiguous_bare_reference_raises(self):
        with pytest.raises(ParseError, match="Unresolvable attachment reference"):
            parse_new_recruit_wtc(
                make_list(
                    "Char1: 1x Captain (80 pts): Warlord",
                    "Leading Intercessors",
                    "5x Intercessors (80 pts)",
                    "5x Intercessors (80 pts)",
                )
            )

    def test_out_of_range_index_raises(self):
        with pytest.raises(ParseError, match="Unresolvable attachment reference"):
            parse_new_recruit_wtc(
                make_list(
                    "Char1: 1x Captain (80 pts): Warlord",
                    "Leading Intercessors[2]",
                    "5x Intercessors (80 pts)",
                )
            )

    def test_leader_on_two_bodyguards_raises(self):
        with pytest.raises(ParseError, match="Leader attached to two units"):
            parse_new_recruit_wtc(
                make_list(
                    "Char1: 1x Captain (80 pts): Warlord",
                    "Leading Intercessors[1]",
                    "5x Intercessors (80 pts)",
                    "5x Intercessors (80 pts)",
                    "  Attached to Captain",
                )
            )


class TestFraming:
    def test_text_around_the_export_is_ignored(self):
        # nr_wtc_3's source had a preamble; Reddit posts add commentary after.
        text = (EXAMPLES / "nr_wtc_5.txt").read_text()
        army_list = parse_new_recruit_wtc(
            "My list, thoughts?\n\n" + text + "\nThanks in advance!\n"
        )

        assert len(army_list.units) == 10

    def test_crlf_and_trailing_whitespace_parse(self):
        # Pastes from Windows and Reddit's editor ("  " hard breaks).
        text = (EXAMPLES / "nr_wtc_6.txt").read_text()
        army_list = parse_new_recruit_wtc(text.replace("\n", "  \r\n"))

        assert len(army_list.units) == 18
        assert army_list.disposition == "Priority Assets"

    def test_missing_closing_rule_raises(self):
        with pytest.raises(ParseError, match=r"No \+\+\+ ruled header block"):
            parse_new_recruit_wtc(
                "++++++++++++++++++++\n+ FACTION KEYWORD: Xenos - Orks\n"
            )

    def test_body_line_before_first_unit_raises(self):
        # New Recruit's GW-style export shares the header but not the body.
        with pytest.raises(ParseError, match="Body line before the first unit"):
            parse_new_recruit_wtc(make_list("Attached Units", "1x Trukk (60 pts)"))

    def test_unit_count_mismatch_raises(self):
        text = (EXAMPLES / "nr_wtc_5.txt").read_text()
        with pytest.raises(ParseError, match="declares 10 units but the list has 9"):
            parse_new_recruit_wtc(text.replace("1x Trukk (60 pts)", "Trukk", 1))

    def test_header_without_unit_count_skips_the_check(self):
        army_list = parse_new_recruit_wtc(
            make_list("1x Trukk (60 pts)", number_of_units=None)
        )

        assert len(army_list.units) == 1


def make_list(*body: str, number_of_units: int | None = -1) -> str:
    """A minimal WTC export around `body`; NUMBER OF UNITS counts unit headers."""
    if number_of_units == -1:
        number_of_units = sum(1 for line in body if is_unit_header(line))
    header = [
        "+++++++++++++++++++++++++++++++++++++++++++++++",
        "+ FACTION KEYWORD: Imperium - Adeptus Astartes",
        "+ DETACHMENT: Gladius Task Force (Combat Doctrines)",
        "+ FORCE DISPOSITION: Purge the Foe",
        "+ TOTAL ARMY POINTS: 2000pts",
    ]
    if number_of_units is not None:
        header.append(f"+ NUMBER OF UNITS: {number_of_units}")
    header.append("+++++++++++++++++++++++++++++++++++++++++++++++")
    return "\n".join([*header, "", *body, "", "Created with newrecruit.eu v35.82"])
