import pytest

from listgrok import ArmyList, ParseError
from listgrok.parsers.official_app.header import parse_header, split_detachments


def test_official_1_header_has_no_super_faction():
    army_list = ArmyList()
    parse_header(
        [
            "T’au Empire",
            "Retaliation Cadre (3 Detachment Points)",
            "Purge the Foe",
            "Strike Force (2,000 Points)",
        ],
        army_list,
    )

    assert army_list.super_faction == ""
    assert army_list.faction == "T’au Empire"
    assert army_list.detachments == ["Retaliation Cadre"]
    assert army_list.detachment_points == 3
    assert army_list.disposition == "Purge the Foe"
    assert army_list.army_size == "Strike Force"
    assert army_list.army_size_points == 2000


def test_official_2_header_has_a_super_faction_and_three_detachments():
    army_list = ArmyList()
    parse_header(
        [
            "Space Marines",
            "Space Wolves",
            (
                "Champions of Fenris, Legends of Saga and Song and Veterans of the Fang"
                " (3 Detachment Points)"
            ),
            "Disruption",
            "Strike Force (2,000 Points)",
        ],
        army_list,
    )

    assert army_list.super_faction == "Space Marines"
    assert army_list.faction == "Space Wolves"
    assert army_list.detachments == [
        "Champions of Fenris",
        "Legends of Saga and Song",
        "Veterans of the Fang",
    ]
    assert army_list.detachment_points == 3
    assert army_list.disposition == "Disruption"
    assert army_list.army_size == "Strike Force"
    assert army_list.army_size_points == 2000


def test_faction_only_header_leaves_disposition_empty():
    army_list = ArmyList()
    parse_header(
        [
            "T’au Empire",
            "Retaliation Cadre (3 Detachment Points)",
            "Strike Force (2,000 Points)",
        ],
        army_list,
    )

    assert army_list.faction == "T’au Empire"
    assert army_list.disposition == ""


@pytest.mark.parametrize(
    "line,expected",
    [
        ("Retaliation Cadre", ["Retaliation Cadre"]),
        # A single detachment whose own name contains "and" is never split.
        ("Legends of Saga and Song", ["Legends of Saga and Song"]),
        (
            "Champions of Fenris, Legends of Saga and Song and Veterans of the Fang",
            [
                "Champions of Fenris",
                "Legends of Saga and Song",
                "Veterans of the Fang",
            ],
        ),
        (
            "Champions of Fenris, Veterans of the Fang",
            ["Champions of Fenris", "Veterans of the Fang"],
        ),
    ],
)
def test_split_detachments(line, expected):
    assert split_detachments(line) == expected


def test_missing_army_size_line_raises():
    with pytest.raises(ParseError):
        parse_header(
            [
                "T’au Empire",
                "Retaliation Cadre (3 Detachment Points)",
                "Purge the Foe",
            ],
            ArmyList(),
        )


def test_missing_detachment_line_raises():
    with pytest.raises(ParseError):
        parse_header(
            ["T’au Empire", "Purge the Foe", "Strike Force (2,000 Points)"],
            ArmyList(),
        )


def test_too_many_faction_lines_raises():
    with pytest.raises(ParseError):
        parse_header(
            [
                "One",
                "Two",
                "Three",
                "Four",
                "Retaliation Cadre (3 Detachment Points)",
                "Strike Force (2,000 Points)",
            ],
            ArmyList(),
        )
