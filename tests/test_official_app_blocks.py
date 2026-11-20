import time

import pytest

from listgrok import ParseError
from listgrok.parsers.official_app import parse_official_app
from listgrok.parsers.official_app.blocks import (
    BlockKind,
    classify_blocks,
    parse_points,
)

# Cases citing official_1 to official_10 were trimmed from exports since
# removed from examples/; they remain in git history, e.g.
# `git show 6bc7874:examples/official_app/official_3.txt`.

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


def test_army_name_containing_a_blank_line_is_one_block():
    # official_7.txt: the name is "Round 2 list", blank line, "QFP".
    text = "Round 2 list\n\nQFP (2,000 Points)\n\n" + NO_ARMY_NAME
    blocks = classify_blocks(text)

    assert blocks[0].kind == BlockKind.ARMY_NAME
    assert blocks[0].lines == ("Round 2 list", "", "QFP (2,000 Points)")
    assert blocks[1].kind == BlockKind.HEADER


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


HEADER = """T’au Empire
Retaliation Cadre (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

"""


def kinds_after_header(body):
    blocks = classify_blocks(HEADER + body)
    return [(b.kind, b.lines[0]) for b in blocks[1:]]


def test_new_recruit_footer_is_a_trailer():
    # nr_official_3.txt
    footer = "Exported with New Recruit v37.14, Data Version: v8"

    assert kinds_after_header(f"CHARACTERS\n\n{footer}\n")[-1] == (
        BlockKind.TRAILER,
        footer,
    )


@pytest.mark.parametrize(
    "footer",
    [
        "Exported with App Version: v2.6.0",
        "Exported with App Version: " + "v" * 100 + ", Data Version: v946",
    ],
)
def test_official_footer_is_a_trailer_without_a_nearby_data_version(footer):
    # Synthetic, varying official_1.txt's footer: the app's own prefix is enough.
    assert kinds_after_header(f"CHARACTERS\n\n{footer}\n")[-1] == (
        BlockKind.TRAILER,
        footer,
    )


def test_other_lone_exported_with_line_still_raises():
    # Synthetic: no fixture has a footer from an unknown exporter.
    with pytest.raises(ParseError, match="Unrecognised lone line"):
        classify_blocks(HEADER + "Exported with love\n")


def test_group_heading_fused_with_its_units_splits_out_each_unit():
    # nr_official_4.txt
    body = """Attached unit 1
Marneus Calgar (180 Points)
  • Attached as: Leader (Character)
Bladeguard Veteran Squad (180 Points)
  • Attached as: Bodyguard
"""

    blocks = classify_blocks(HEADER + body)[1:]

    assert [b.kind for b in blocks] == [
        BlockKind.GROUP,
        BlockKind.UNIT,
        BlockKind.UNIT,
    ]
    assert blocks[1].lines == (
        "Marneus Calgar (180 Points)",
        "  • Attached as: Leader (Character)",
    )
    assert blocks[2].lines[0] == "Bladeguard Veteran Squad (180 Points)"


def test_underline_under_a_group_heading_is_dropped():
    # official_31.txt: each group heading is underlined, with no blank line
    # before its first unit.
    body = """Attached unit 1
============
Marneus Calgar (180 Points)
  • Attached as: Leader (Character)
"""

    blocks = classify_blocks(HEADER + body)[1:]

    assert [(b.kind, b.lines) for b in blocks] == [
        (BlockKind.GROUP, ("Attached unit 1",)),
        (
            BlockKind.UNIT,
            (
                "Marneus Calgar (180 Points)",
                "  • Attached as: Leader (Character)",
            ),
        ),
    ]


def test_underline_after_a_blank_line_under_a_group_heading_is_dropped():
    # Synthetic, from official_31.txt: a blank line between the heading and
    # its underline.
    body = """Attached unit 1

============

Marneus Calgar (180 Points)
  • Attached as: Leader (Character)
"""

    blocks = classify_blocks(HEADER + body)[1:]

    assert [b.kind for b in blocks] == [BlockKind.GROUP, BlockKind.UNIT]


def test_underline_fused_with_the_unit_after_a_blank_line_is_dropped():
    # Synthetic, from official_31.txt: the underline starts the unit's block.
    body = """Attached unit 1

============
Marneus Calgar (180 Points)
  • Attached as: Leader (Character)
"""

    blocks = classify_blocks(HEADER + body)[1:]

    assert [(b.kind, b.lines[0]) for b in blocks] == [
        (BlockKind.GROUP, "Attached unit 1"),
        (BlockKind.UNIT, "Marneus Calgar (180 Points)"),
    ]


@pytest.mark.parametrize(
    "body",
    [
        "Attached unit 1\n============\n============\nA (5 Points)\n  • 1x B\n",
        "Attached unit 1\n============\n\n============\n\nA (5 Points)\n  • 1x B\n",
    ],
)
def test_second_underline_under_a_group_heading_still_raises(body):
    # Synthetic: only the heading's own underline is decoration.
    with pytest.raises(ParseError, match="Unrecognised lone line"):
        classify_blocks(HEADER + body)


@pytest.mark.parametrize(
    "body",
    [
        "ATTACHED UNITS\n============\nAttached unit 1\nA (5 Points)\n  • 1x B\n",
        "ATTACHED UNITS\n\n============\n\nAttached unit 1\n\nA (5 Points)\n",
        "OTHER DATASHEETS\n============\nA (5 Points)\n• 1x B\n",
    ],
)
def test_underline_under_a_section_heading_is_dropped(body):
    # Synthetic, from official_31.txt's underlined group headings.
    blocks = classify_blocks(HEADER + body)[1:]

    assert [b.lines[0].strip() for b in blocks if b.kind is BlockKind.SECTION] == [
        body.split("\n", 1)[0]
    ]
    assert not any("=" in line for b in blocks for line in b.lines)


def test_underline_fused_with_the_header_block_is_dropped():
    # Synthetic, after nr_official_2.txt: no blank line after the header.
    body = "ATTACHED UNITS\n============\n\nA (5 Points)\n  • 1x B\n"

    blocks = classify_blocks(HEADER.rstrip("\n") + "\n" + body)

    assert [b.kind for b in blocks] == [
        BlockKind.HEADER,
        BlockKind.SECTION,
        BlockKind.UNIT,
    ]


def test_lone_underline_outside_a_group_heading_still_raises():
    # Synthetic: only a group heading's underline is known to be decoration.
    with pytest.raises(ParseError, match="Unrecognised lone line"):
        classify_blocks(HEADER + "============\n")


@pytest.mark.parametrize(
    "body_line",
    ["  1x Relic (5 Points)", "• 1x Relic (5 Points)", "◦ 1x Relic (5 Points)"],
)
def test_indented_or_bulleted_points_line_does_not_start_a_unit(body_line):
    # Synthetic: no fixture has a body line with a "(N Points)" suffix.
    body = f"Marneus Calgar (180 Points)\n{body_line}\n"

    assert [kind for kind, _ in kinds_after_header(body)] == [BlockKind.UNIT]


@pytest.mark.parametrize(
    "transform",
    [
        pytest.param(lambda line: line + "\r", id="crlf"),
        pytest.param(lambda line: line + " ", id="trailing-space"),
        pytest.param(lambda line: " " + line, id="uniform-indent"),
    ],
)
def test_fused_units_split_despite_surrounding_whitespace(transform):
    # nr_official_4.txt, with its line endings or margin altered.
    body = """Marneus Calgar (180 Points)
  • Attached as: Leader (Character)
Bladeguard Veteran Squad (180 Points)
  • Attached as: Bodyguard
"""
    body = "\n".join(transform(line) for line in body.splitlines())

    blocks = classify_blocks(HEADER + body)[1:]

    assert [b.kind for b in blocks] == [BlockKind.UNIT, BlockKind.UNIT]


def test_group_heading_between_fused_units_splits_out():
    # Synthetic, a further fusing of nr_official_4.txt: see issue #31.
    body = """Attached unit 1
Marneus Calgar (180 Points)
  • Attached as: Leader (Character)
Attached unit 2
Terminator Squad (380 Points)
  • Attached as: Bodyguard
"""

    assert kinds_after_header(body) == [
        (BlockKind.GROUP, "Attached unit 1"),
        (BlockKind.UNIT, "Marneus Calgar (180 Points)"),
        (BlockKind.GROUP, "Attached unit 2"),
        (BlockKind.UNIT, "Terminator Squad (380 Points)"),
    ]


def test_section_heading_and_footer_after_a_unit_split_out():
    # Synthetic, a further fusing of nr_official_3.txt: see issue #31.
    footer = "Exported with New Recruit v37.14, Data Version: v8"
    body = f"""Marneus Calgar (180 Points)
  • 1x Gauntlets of Ultramar
OTHER DATASHEETS
Scout Squad (65 Points)
  • 5x Scout
{footer}
"""

    assert kinds_after_header(body) == [
        (BlockKind.UNIT, "Marneus Calgar (180 Points)"),
        (BlockKind.SECTION, "OTHER DATASHEETS"),
        (BlockKind.UNIT, "Scout Squad (65 Points)"),
        (BlockKind.TRAILER, footer),
    ]


def test_section_group_and_first_unit_in_one_block_split_out():
    # Synthetic, a further fusing of nr_official_4.txt: see issue #31.
    body = """ATTACHED UNITS
Attached unit 1
Marneus Calgar (180 Points)
  • Warlord
"""

    assert kinds_after_header(body) == [
        (BlockKind.SECTION, "ATTACHED UNITS"),
        (BlockKind.GROUP, "Attached unit 1"),
        (BlockKind.UNIT, "Marneus Calgar (180 Points)"),
    ]


@pytest.mark.parametrize(
    "run_line",
    ["Enhancements: Relic (15 Points)", "1x Relic (5 Points)", "BOLT PISTOL"],
)
def test_unindented_body_line_stays_in_its_compact_unit(run_line):
    # Synthetic, in official_3.txt's shape: compact run lines sit at column 0,
    # so only indentation elsewhere in a block makes column 0 mean anything.
    body = f"Captain (80 Points)\n• Warlord\n{run_line}\n"

    assert [kind for kind, _ in kinds_after_header(body)] == [BlockKind.UNIT]


def test_unit_named_like_a_group_heading_is_a_unit():
    # Synthetic: the "(N Points)" suffix outranks the "Attached unit" prefix.
    body = "Attached Unit of Doom (90 Points)\n  • 1x Foo\n"

    assert kinds_after_header(body) == [
        (BlockKind.UNIT, "Attached Unit of Doom (90 Points)"),
    ]


def test_second_header_starting_with_its_size_line_stays_a_header():
    # Synthetic: official_1.txt's header reordered, as if two lists were pasted.
    body = (
        "Strike Force (2,000 Points)\nT’au Empire\n"
        "Retaliation Cadre (3 Detachment Points)\nPurge the Foe\n"
    )

    assert kinds_after_header(body) == [
        (BlockKind.HEADER, "Strike Force (2,000 Points)"),
    ]


def test_many_fused_group_headings_do_not_overflow_the_stack():
    # Crafted input, not an export: one block per heading used to mean one
    # stack frame per heading.
    blocks = classify_blocks(HEADER + "Attached unit 1\n" * 5000)

    assert len(blocks) == 5001


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


def test_army_name_without_a_points_suffix_is_one_block():
    # official_28: the name line carries no "(N Points)" suffix. Everything
    # before the header is the army name.
    blocks = classify_blocks("No more Overwatch\n\n" + NO_ARMY_NAME)

    assert blocks[0].kind is BlockKind.ARMY_NAME
    assert blocks[0].lines == ("No more Overwatch",)
    assert blocks[1].kind is BlockKind.HEADER


def test_everything_before_the_header_is_one_army_name_block():
    # Any text up to the header belongs to the block, blank separators
    # included. Splitting the name from trailing notes is the fold's job
    # (TestArmyNameFold).
    text = "Name (2,000 Points)\n\nnotes one\nnotes two\n\n" + NO_ARMY_NAME
    blocks = classify_blocks(text)

    assert blocks[0].kind is BlockKind.ARMY_NAME
    assert blocks[0].lines == (
        "Name (2,000 Points)",
        "",
        "notes one",
        "notes two",
    )
    assert blocks[1].kind is BlockKind.HEADER


def test_title_case_lone_line_after_the_header_raises():
    # A section heading the app hasn't been seen writing ("Other Datasheets"
    # rather than "OTHER DATASHEETS") must not be guessed as a GROUP — that
    # would silently stamp a fake attachment group onto every unit after it.
    with pytest.raises(ParseError):
        classify_blocks(NO_ARMY_NAME + "\nOther Datasheets\n")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2,000", 2000),
        ("70", 70),
        ("1,260", 1260),
        # listhammer_adeptus_custodes, _tau_empire, _tyranids, _orks_fr.
        ("2.000", 2000),
        ("2'000", 2000),
        ("2\u00a0000", 2000),
        ("2\u202f000", 2000),
        # Seen in Listhammer lists not kept as fixtures.
        ("2 000", 2000),
        ("2’000", 2000),
    ],
)
def test_parse_points_strips_thousands_separators(text, expected):
    assert parse_points(text) == expected


@pytest.mark.parametrize("sep", [".", "'", "’", " ", "\u00a0", "\u202f"])
def test_army_size_with_a_thousands_separator_parses(sep):
    army_list = parse_official_app(NO_ARMY_NAME.replace("2,000", f"2{sep}000"))

    assert army_list.army_size_points == 2000


def test_footnoted_unit_header_and_its_footnote_block():
    # listhammer_chaos_knights: "*" after the points marks a unit the
    # footnote block below it describes.
    body = (
        "CHARACTERS\n\nWar Dog Karnivore (145 Points)*\n• Warlord\n"
        "• 1x Slaughterclaw\n\n* This Datasheet also has the Battleline keyword\n"
    )

    assert kinds_after_header(body) == [
        (BlockKind.SECTION, "CHARACTERS"),
        (BlockKind.UNIT, "War Dog Karnivore (145 Points)*"),
        (BlockKind.FOOTNOTE, "* This Datasheet also has the Battleline keyword"),
    ]


@pytest.mark.parametrize(
    "heading",
    [
        "ERRORS",  # listhammer_adeptus_custodes_errors
        "ERREURS",  # listhammer_orks_fr
        "FEHLER",  # the German app's "Fehler", upper-cased as the others are
        "Errors",  # synthetic: case and a trailing colon are tolerated
        "ERRORS:",
    ],
)
def test_validation_errors_block_is_classified(heading):
    body = f"{heading}\n• Invalid wargear selected.\n\nCHARACTERS\n"

    assert kinds_after_header(body) == [
        (BlockKind.VALIDATION_ERRORS, heading),
        (BlockKind.SECTION, "CHARACTERS"),
    ]


@pytest.mark.parametrize(
    "following,kind",
    [
        ("ATTACHED UNITS", BlockKind.SECTION),
        ("Attached Unit 1", BlockKind.GROUP),
        ("Boss (80 Points)", BlockKind.UNIT),
    ],
)
def test_validation_errors_block_ends_at_its_first_unbulleted_line(following, kind):
    # Synthetic: an errors block with no blank line after it, as New Recruit
    # can fuse blocks.
    assert kinds_after_header(f"ERRORS\n• a\n{following}\n") == [
        (BlockKind.VALIDATION_ERRORS, "ERRORS"),
        (kind, following),
    ]


def test_validation_errors_block_fused_onto_the_header_splits_out():
    # listhammer_adeptus_custodes_errors: no blank line after the size line.
    blocks = classify_blocks(HEADER.rstrip("\n") + "\nERRORS\n• Invalid.\n")

    assert [(b.kind, b.lines) for b in blocks[1:]] == [
        (BlockKind.VALIDATION_ERRORS, ("ERRORS", "• Invalid.")),
    ]


@pytest.mark.parametrize(
    "heading",
    [
        "Unité Attachée 1",  # listhammer_orks_fr
        "Unité 1 Attachée",  # listhammer_adeptus_mechanicus_fr
        "Angeschlossene Einheit 1",  # listhammer_world_eaters_de
    ],
)
def test_localised_group_heading_is_a_group(heading):
    assert kinds_after_header(f"{heading}\n") == [(BlockKind.GROUP, heading)]


@pytest.mark.parametrize(
    "section,group",
    [
        ("Unités Attachées", "Unité 1 Attachée"),
        ("Angeschlossene Einheiten", "Angeschlossene Einheit 1"),
    ],
)
def test_localised_fused_section_and_group_split(section, group):
    assert kinds_after_header(f"{section}\n{group}\n") == [
        (BlockKind.SECTION, section),
        (BlockKind.GROUP, group),
    ]


@pytest.mark.parametrize(
    "detachment_line",
    [
        "Cohort Cybernetica (3 Points de Détachement)",  # listhammer_*_fr
        "Freeblade Company (3 Kontingentspunkte)",  # listhammer_*_de
    ],
)
def test_localised_detachment_line_marks_the_header(detachment_line):
    blocks = classify_blocks(f"Army\n\nFaction\n{detachment_line}\n\nCHARACTERS\n")

    assert [b.kind for b in blocks] == [
        BlockKind.ARMY_NAME,
        BlockKind.HEADER,
        BlockKind.SECTION,
    ]


@pytest.mark.parametrize(
    "footer",
    [
        # listhammer_orks_fr, listhammer_world_eaters_de.
        "Exporté avec la Version de l'Appli : v2.7.2 (2), Version de Données : v972",
        "Exportiert mit App-Version v2.7.1 (146), Datenversion: v972",
    ],
)
def test_localised_footer_is_a_trailer(footer):
    assert kinds_after_header(f"CHARACTERS\n\n{footer}\n")[-1] == (
        BlockKind.TRAILER,
        footer,
    )


def test_army_name_with_a_long_whitespace_run_classifies_in_linear_time():
    # Crafted input, not an export: the name's lazy ".+?" and the "\s+" before
    # the parenthetical both matched spaces, which took ~10s on this run.
    name = "a" + " " * 100_000 + "b"

    start = time.perf_counter()
    blocks = classify_blocks(f"{name} (2,000 Points)\n\n" + NO_ARMY_NAME)

    assert time.perf_counter() - start < 1
    assert blocks[0].kind is BlockKind.ARMY_NAME


def test_oversized_detachment_points_raise_parse_error():
    # Crafted input, not an export: digit runs past Python's 4300-digit int()
    # limit used to escape as ValueError rather than ParseError.
    with pytest.raises(ParseError):
        classify_blocks(
            NO_ARMY_NAME.replace("(3 Detachment", "(" + "9" * 5000 + " Detachment")
        )


def test_oversized_army_points_stay_part_of_the_name():
    # Crafted input, not an export: a points suffix too long to be one is not
    # read as the list total (int() would raise past 4300 digits), so the
    # whole line is the name and points stays None.
    line = "Army (" + "9" * 5000 + " Points)"

    army_list = parse_official_app(line + "\n\n" + NO_ARMY_NAME)

    assert army_list.name == line
    assert army_list.points is None


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            "Attached unit 1\nCaptain (80 Points)\n• Attached as: Leader\n"
            "• 1x Bolt pistol\n",
            id="group-then-compact-unit",
        ),
        pytest.param(
            "Attached Units\nAttached unit 1\nCaptain (80 Points)\n"
            "• Attached as: Leader\n• 1x Bolt pistol\n",
            id="title-case-section-group-then-compact-unit",
        ),
    ],
)
def test_group_heading_fused_with_a_compact_unit_splits_out(body):
    # Synthetic, nr_official_4.txt's fusing in the compact dialect's
    # unindented body: a group heading is a lone line, so the line after it
    # starts a block whatever the body's indentation.
    assert kinds_after_header(body)[-2:] == [
        (BlockKind.GROUP, "Attached unit 1"),
        (BlockKind.UNIT, "Captain (80 Points)"),
    ]


def test_group_heading_after_a_compact_unit_splits_out():
    # Synthetic, as above: the next group follows a compact unit directly.
    body = (
        "Attached unit 1\nCaptain (80 Points)\n• Attached as: Leader\n"
        "• 1x Bolt pistol\nAttached unit 2\nLieutenant (70 Points)\n"
        "• Attached as: Leader\n• 1x Bolt pistol\n"
    )

    assert kinds_after_header(body) == [
        (BlockKind.GROUP, "Attached unit 1"),
        (BlockKind.UNIT, "Captain (80 Points)"),
        (BlockKind.GROUP, "Attached unit 2"),
        (BlockKind.UNIT, "Lieutenant (70 Points)"),
    ]


def test_unit_header_fused_into_a_compact_body_raises():
    # Synthetic: in an unindented body a fused unit header cannot be told from
    # a run line by indentation, so rather than swallow it into the previous
    # unit's decorations (and drop its points), the parse fails.
    body = (
        "Captain (80 Points)\n• Warlord\n• 1x Bolt pistol\n"
        "Lieutenant (70 Points)\n• 1x Bolt pistol\n"
    )

    with pytest.raises(ParseError, match="Unit header inside a compact body"):
        classify_blocks(HEADER + body)


@pytest.mark.parametrize("tail", ["CHARACTERS", "Attached unit 1"])
def test_heading_fused_onto_the_header_block_splits_out(tail):
    # Synthetic, a further fusing of nr_official_3.txt: no blank line between
    # the header and the first heading.
    blocks = classify_blocks(HEADER.rstrip("\n") + f"\n{tail}\n")

    assert blocks[0].kind is BlockKind.HEADER
    assert tail not in blocks[0].lines
    assert (blocks[1].kind, blocks[1].lines) in [
        (BlockKind.SECTION, (tail,)),
        (BlockKind.GROUP, (tail,)),
    ]
