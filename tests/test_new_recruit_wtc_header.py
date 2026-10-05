import pytest

from listgrok import ArmyList, ParseError
from listgrok.parsers.new_recruit_wtc.header import parse_header, split_detachments


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
        assert army_list.super_faction == "Chaos"
        assert army_list.faction == "World Eaters"
        assert army_list.detachments == ["Possessed Slaughterband", "Vessels of Wrath"]
        assert army_list.disposition == "Purge the Foe"
        assert army_list.points == 2000

    def test_three_part_faction_keeps_first_and_last(self):
        # nr_wtc_9: the Adeptus Astartes middle part is dropped.
        army_list = ArmyList()
        parse_header(
            header(
                "+ FACTION KEYWORD: Imperium - Adeptus Astartes - Black Templars",
                "+ TOTAL ARMY POINTS: 990pts",
            ),
            army_list,
        )

        assert army_list.super_faction == "Imperium"
        assert army_list.faction == "Black Templars"

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

    def test_unknown_keys_are_ignored(self):
        # nr_official_4 (Reddit) carries a PLAYER NAME line.
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
