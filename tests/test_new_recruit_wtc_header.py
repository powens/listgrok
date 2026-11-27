import pytest

from listgrok import ArmyList, ParseError
from listgrok.parsers.new_recruit_wtc.header import (
    _detachment_name_regex,
    parse_header,
    split_detachments,
)


def header(*lines: str) -> list[str]:
    return list(lines)


class TestParseHeader:
    def test_reads_faction_points_detachment_and_disposition(self):
        # nr_wtc_2
        army_list = ArmyList()
        declared = parse_header(
            header(
                "+ FACTION KEYWORD: Chaos - World Eaters",
                "+ DETACHMENT: Possessed Slaughterband, Vessels of Wrath (Brazen Fury)",
                "+ FORCE DISPOSITION: Purge the Foe",
                "+ TOTAL ARMY POINTS: 2000pts",
                "+",
                "+ WARLORD: Char1: Daemon Prince of Khorne",
                "+ ENHANCEMENT: Frenzied Focus (on Char3: Slaughterbound)",
                "+ NUMBER OF UNITS: 13",
                "+ SECONDARY: - Bring It Down: (3x2) - Assassination: 4 Characters",
            ),
            army_list,
        )

        assert declared == 13
        assert army_list.super_faction == ""
        assert army_list.faction == "World Eaters"
        assert army_list.detachments == ["Possessed Slaughterband", "Vessels of Wrath"]
        assert army_list.disposition == "Purge the Foe"
        assert army_list.points == 2000

    def test_three_part_faction_maps_parent_to_official_name(self):
        # nr_wtc_9: the Imperium alliance is dropped; the parent faction is
        # super_faction, under the official app's name for it.
        army_list = ArmyList()
        parse_header(
            header(
                "+ FACTION KEYWORD: Imperium - Adeptus Astartes - Black Templars",
                "+ TOTAL ARMY POINTS: 990pts",
            ),
            army_list,
        )

        assert army_list.super_faction == "Space Marines"
        assert army_list.faction == "Black Templars"

    @pytest.mark.parametrize(
        ("keyword", "faction"),
        [
            ("Imperium - Adeptus Astartes", "Space Marines"),
            ("Chaos - Heretic Astartes", "Chaos Space Marines"),
        ],
    )
    def test_two_part_faction_maps_to_official_name(self, keyword, faction):
        # Not in a fixture: vanilla Space Marines and Chaos Space Marines lists,
        # named as the official app exports name them (e.g. lvo2026 CSM lists).
        army_list = ArmyList()
        parse_header(
            header(f"+ FACTION KEYWORD: {keyword}", "+ TOTAL ARMY POINTS: 2000pts"),
            army_list,
        )

        assert army_list.super_faction == ""
        assert army_list.faction == faction

    def test_unmapped_parent_faction_passes_through(self):
        # Not in a fixture: a parent keyword with no official-app name mapped.
        army_list = ArmyList()
        parse_header(
            header(
                "+ FACTION KEYWORD: Imperium - Some Parent - Some Faction",
                "+ TOTAL ARMY POINTS: 1000pts",
            ),
            army_list,
        )

        assert army_list.super_faction == "Some Parent"

    def test_single_part_faction_leaves_super_faction_empty(self):
        army_list = ArmyList()
        parse_header(
            header("+ FACTION KEYWORD: Orks", "+ TOTAL ARMY POINTS: 995pts"),
            army_list,
        )

        assert army_list.super_faction == ""
        assert army_list.faction == "Orks"

    def test_non_breaking_spaces_become_plain_spaces(self):
        # nr_wtc_1: New Recruit writes U+00A0 inside detachment and
        # disposition values.
        army_list = ArmyList()
        parse_header(
            header(
                "+ FACTION KEYWORD: Chaos - World Eaters",
                "+ DETACHMENT: Berzerker\xa0Warband (Relentless\xa0Rage)",
                "+ FORCE DISPOSITION: Purge\xa0the\xa0Foe",
                "+ TOTAL ARMY POINTS: 2000pts",
            ),
            army_list,
        )

        assert army_list.detachments == ["Berzerker Warband"]
        assert army_list.disposition == "Purge the Foe"

    def test_ampersand_continuation_lines_are_skipped(self):
        # nr_wtc_6: a multi-unit ENHANCEMENT wraps onto "&" lines.
        army_list = ArmyList()
        declared = parse_header(
            header(
                "+ FACTION KEYWORD: Xenos - Tyranids",
                "+ TOTAL ARMY POINTS: 1995pts",
                "+ ENHANCEMENT: Parasitic Biomorphology (on Char2: Broodlord)",
                "& Regenerating Monstrosity (on Char3: Tyranid Prime with Lash Whip)",
                "& Ocular Adaptation (on Char4: Tyranid Prime with Lash Whip)",
                "+ NUMBER OF UNITS: 18",
            ),
            army_list,
        )

        assert declared == 18

    def test_missing_number_of_units_returns_none(self):
        army_list = ArmyList()
        declared = parse_header(
            header("+ FACTION KEYWORD: Xenos - Orks", "+ TOTAL ARMY POINTS: 995pts"),
            army_list,
        )

        assert declared is None

    @pytest.mark.parametrize("value", ["²", "lots", "-1", ""])
    def test_unreadable_number_of_units_raises(self, value):
        # Not in a fixture: "²" passes str.isdigit() but int() rejects it.
        with pytest.raises(ParseError, match="Unreadable NUMBER OF UNITS"):
            parse_header(
                header(
                    "+ FACTION KEYWORD: Xenos - Orks",
                    "+ TOTAL ARMY POINTS: 995pts",
                    f"+ NUMBER OF UNITS: {value}",
                ),
                ArmyList(),
            )

    def test_unknown_keys_are_ignored(self):
        # Not in a fixture: an unknown key such as PLAYER NAME.
        army_list = ArmyList()
        parse_header(
            header(
                "+ PLAYER NAME: Someone",
                "+ FACTION KEYWORD: Imperium - Adeptus Custodes",
                "+ TOTAL ARMY POINTS: 2000pts",
            ),
            army_list,
        )

        assert army_list.faction == "Adeptus Custodes"

    def test_missing_faction_raises(self):
        with pytest.raises(ParseError, match="FACTION KEYWORD"):
            parse_header(header("+ TOTAL ARMY POINTS: 2000pts"), ArmyList())

    def test_missing_points_raises(self):
        with pytest.raises(ParseError, match="TOTAL ARMY POINTS"):
            parse_header(header("+ FACTION KEYWORD: Xenos - Orks"), ArmyList())

    def test_unreadable_points_raises(self):
        with pytest.raises(ParseError, match="TOTAL ARMY POINTS"):
            parse_header(
                header(
                    "+ FACTION KEYWORD: Xenos - Orks",
                    "+ TOTAL ARMY POINTS: lots",
                ),
                ArmyList(),
            )

    def test_line_without_a_key_raises(self):
        # A Reddit paste with markdown escapes: "\+ FACTION KEYWORD: ...".
        with pytest.raises(ParseError, match="Unrecognised header line"):
            parse_header(header("\\+ FACTION KEYWORD: Xenos - Orks"), ArmyList())


class TestSplitDetachments:
    def test_single_detachment_drops_the_rule(self):
        # nr_wtc_0
        assert split_detachments("Lions of the Emperor (Against All Odds)") == [
            "Lions of the Emperor"
        ]

    def test_comma_separated_detachments(self):
        # nr_wtc_3
        assert split_detachments(
            "Court of the Phoenician, Spectacle of Slaughter (Sensational Performance)"
        ) == ["Court of the Phoenician", "Spectacle of Slaughter"]

    def test_and_inside_a_name_is_not_split(self):
        # Unlike official_app, WTC separates detachments with commas only.
        assert split_detachments("Kult of Speed and More Dakka (Waaagh!)") == [
            "Kult of Speed and More Dakka"
        ]

    @pytest.mark.parametrize(
        "name",
        [
            "Ordo Xenos, Alien Hunters",
            "Ordo Malleus, Daemon Hunters",
            "Ordo Hereticus, Purgation Force",
        ],
    )
    def test_every_ordo_detachment_stays_whole(self, name):
        # Not in a fixture (from review): every comma name in COMPOUND_DETACHMENTS.
        assert split_detachments(f"{name}, Lions of the Emperor (Rule)") == [
            name,
            "Lions of the Emperor",
        ]

    def test_comma_inside_a_known_name_is_not_split(self):
        # Not in a fixture: a detachment name with a comma in it.
        assert split_detachments(
            "Ordo Xenos, Alien Hunters, Lions of the Emperor (Rule)"
        ) == ["Ordo Xenos, Alien Hunters", "Lions of the Emperor"]
        assert split_detachments(
            "Lions of the Emperor, Ordo Xenos, Alien Hunters (Rule)"
        ) == ["Lions of the Emperor", "Ordo Xenos, Alien Hunters"]

    def test_known_name_prefixing_a_longer_name_does_not_split_it(self):
        # Not in a fixture (from review): a known comma name only matches whole.
        assert split_detachments("Ordo Xenos, Alien Hunters Extended (Rule)") == [
            "Ordo Xenos",
            "Alien Hunters Extended",
        ]

    def test_each_detachment_drops_its_own_rule(self):
        # Not in a fixture (from review).
        assert split_detachments("A (RuleA), B (RuleB)") == ["A", "B"]

    def test_rule_with_nested_parentheses_is_dropped(self):
        # Not in a fixture (from review).
        assert split_detachments("Foo (Rule (Aura))") == ["Foo"]

    def test_no_known_comma_names_still_splits_on_commas(self):
        # Not in a fixture (from review): an empty alternation once matched
        # the empty string first and dropped every name.
        regex = _detachment_name_regex(())

        assert [name.strip() for name in regex.findall("A, B")] == ["A", "B"]
