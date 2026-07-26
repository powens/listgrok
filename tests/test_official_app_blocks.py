import pytest

from listgrok import ParseError
from listgrok.parsers.official_app.blocks import (
    BlockKind,
    classify_blocks,
    parse_points,
)

# Trimmed from official_1.txt: one of each block kind.
MINIMAL = """11th stuff (2,000 Points)

T’au Empire
Retaliation Cadre (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

CHARACTERS

Commander Farsight (70 Points)
  • 1x Dawn Blade

Exported with App Version: v2.3.0 (1), Data Version: v912
"""

# Trimmed from official_1.txt: the attached-units section.
ATTACHED = """11th stuff (2,000 Points)

T’au Empire
Retaliation Cadre (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

ATTACHED UNITS

Attached unit 1

Commander Farsight (70 Points)
  • Attached as: Leader (Character)
  • 1x Dawn Blade
"""

NO_ARMY_NAME = """T’au Empire
Retaliation Cadre (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

CHARACTERS

Commander Farsight (70 Points)
  • 1x Dawn Blade
"""

# Trimmed from official_3.txt: the newer dialect writes no blank line between
# the attached-units heading and the first group heading, fusing them into one
# block, and capitalises "Unit" in group headings.
FUSED_ATTACHED = """Orks
Strike Force (2000 points)
Kult of Speed and More Dakka! (3 Detachment Points)
Force Dispositions: Disruption

Attached Units
Attached Unit 1

Zodgrod Wortsnagga (80 points)
• Attached as: Leader (Character)
• 1x Da Grabzappa
1x Squigstoppa

Attached Unit 2

Big Mek with Shokk Attack Gun (70 points)
• Attached as: Leader (Character)
• 1x Close combat weapon
"""


def test_classifies_one_of_each_block_kind():
    assert [block.kind for block in classify_blocks(MINIMAL)] == [
        BlockKind.ARMY_NAME,
        BlockKind.HEADER,
        BlockKind.SECTION,
        BlockKind.UNIT,
        BlockKind.TRAILER,
    ]


def test_group_heading_is_not_a_section_heading():
    # "ATTACHED UNITS" is all caps and is a section; "Attached unit 1" is not.
    assert [block.kind for block in classify_blocks(ATTACHED)] == [
        BlockKind.ARMY_NAME,
        BlockKind.HEADER,
        BlockKind.SECTION,
        BlockKind.GROUP,
        BlockKind.UNIT,
    ]


def test_header_keeps_its_lines_verbatim():
    header = classify_blocks(MINIMAL)[1]

    assert header.lines == (
        "T’au Empire",
        "Retaliation Cadre (3 Detachment Points)",
        "Purge the Foe",
        "Strike Force (2,000 Points)",
    )


def test_unit_block_keeps_its_indented_body():
    unit = classify_blocks(MINIMAL)[3]

    assert unit.lines == ("Commander Farsight (70 Points)", "  • 1x Dawn Blade")


def test_list_with_no_army_name_starts_at_the_header():
    assert [block.kind for block in classify_blocks(NO_ARMY_NAME)] == [
        BlockKind.HEADER,
        BlockKind.SECTION,
        BlockKind.UNIT,
    ]


def test_multi_line_army_name_stays_one_block():
    text = "Line one of the name\nand line two (2,000 Points)\n\n" + NO_ARMY_NAME
    blocks = classify_blocks(text)

    assert blocks[0].kind == BlockKind.ARMY_NAME
    assert blocks[0].lines == ("Line one of the name", "and line two (2,000 Points)")


def test_fused_section_and_group_block_splits_into_two_blocks():
    blocks = classify_blocks(FUSED_ATTACHED)

    assert [block.kind for block in blocks] == [
        BlockKind.HEADER,
        BlockKind.SECTION,
        BlockKind.GROUP,
        BlockKind.UNIT,
        BlockKind.GROUP,
        BlockKind.UNIT,
    ]
    assert blocks[1].lines == ("Attached Units",)
    assert blocks[2].lines == ("Attached Unit 1",)


def test_capitalised_lone_group_heading_is_a_group():
    # official_3.txt: "Attached Unit 2" — the newer dialect capitalises "Unit".
    assert classify_blocks(FUSED_ATTACHED)[4].lines == ("Attached Unit 2",)


def test_text_with_no_header_raises():
    # Some other app's export: no "(N Detachment Points)" line anywhere.
    with pytest.raises(ParseError):
        classify_blocks("+ FACTION KEYWORD: Xenos - T’au Empire\n")


def test_unclassifiable_block_after_the_header_raises():
    with pytest.raises(ParseError):
        classify_blocks(NO_ARMY_NAME + "\nstray line one\nstray line two\n")


def test_unclassifiable_block_before_the_header_raises():
    with pytest.raises(ParseError):
        classify_blocks("stray line\n\n" + NO_ARMY_NAME)


def test_title_case_lone_line_after_the_header_raises():
    # A section heading the app hasn't been seen writing ("Other Datasheets"
    # rather than "OTHER DATASHEETS") must not be guessed as a GROUP — that
    # would silently stamp a fake attachment group onto every unit after it.
    with pytest.raises(ParseError):
        classify_blocks(NO_ARMY_NAME + "\nOther Datasheets\n")


@pytest.mark.parametrize(
    "text,expected", [("2,000", 2000), ("70", 70), ("1,260", 1260)]
)
def test_parse_points_strips_thousands_commas(text, expected):
    assert parse_points(text) == expected
