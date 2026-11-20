"""Split an official-app (11th edition) export into classified blocks.

Classification is by shape alone. The header is the block with a
"(N Detachment Points)" line, which no other block carries: everything before
it is the army name, everything after it is section headings, attachment-group
headings, unit blocks, the app's validation errors, unit footnotes and the
footer. Blocks New Recruit fuses by leaving out blank lines are split apart
here.

The French and German apps translate the fixed labels this module keys on, so
each pattern below accepts their forms too; translated section headings need
nothing, being recognised by shape.

This module is also the home of every regex the parser shares, including
some only units.py and header.py use.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto

from listgrok.exceptions import ParseError

# The patterns below run on untrusted text, so they avoid two hazards. Adjacent
# quantifiers that can both match whitespace backtrack quadratically on a long
# whitespace run, so a name or role always ends in a non-space character.
# Unbounded digit runs reach int(), which raises ValueError past 4300 digits,
# so counts are capped and an oversized one simply fails to match.

# A points value, with or without a thousands separator. The app writes the
# separator its locale uses: "2,000", "2.000", "2'000", or a space, a no-break
# space or a narrow no-break space (listhammer_adeptus_custodes, _tau_empire,
# _tyranids, _orks_fr).
_POINTS_VALUE = r"\d{1,3}(?:[,.'’ \u00a0\u202f]\d{3}){1,2}|\d{1,9}"
# re.DOTALL so a multi-line army name matches as a single name, and \s+ keeps a
# doubled space before the parenthetical ("I choose violence.  (2,000 Points)")
# off the name. "Punkte" is the German app's word. A trailing "*" marks a unit
# a footnote block describes (listhammer_chaos_knights).
POINTS_REGEX = re.compile(
    rf"^(?P<name>.*?\S)\s+\((?P<points>{_POINTS_VALUE})\s(?:[Pp]oints|Punkte)\)\*?$",
    re.DOTALL,
)
DETACHMENT_REGEX = re.compile(
    r"^(?P<name>.+?)\s\((?P<points>\d{1,6})\s"
    r"(?:Detachment\s[Pp]oints?|Points?\sde\sDétachement|Kontingentspunkte?)\)$"
)
NUM_REGEX = re.compile(r"^(?P<num>\d{1,6})x\s(?P<name>.+)$")
# French writes "Attachée en tant que : …", German "Angeschlossen als: …".
ATTACHED_AS_REGEX = re.compile(
    r"^(?:Attached as|Attachée en tant que|Angeschlossen als)\s?:"
    r"\s*(?P<role>[^(\s](?:[^(]*[^(\s])?)\s*"
    r"(?:\((?P<detail>[^)]*)\))?$"
)
BULLET_REGEX = re.compile(r"^[•◦]\s*")
# IGNORECASE: the classic dialect writes "Attached unit 1", the newer one
# "Attached Unit 1". French writes "Unité Attachée 1" or "Unité 1 Attachée",
# German "Angeschlossene Einheit 1". The \b keeps the plural section heading
# ("Attached Units", "Angeschlossene Einheiten") from matching; French's plural
# ("Unités Attachées") fails at the "s".
GROUP_REGEX = re.compile(
    r"^(?:Attached unit|Unité Attachée|Unité \d{1,4} Attachée|Angeschlossene Einheit)\b",
    re.IGNORECASE,
)
# Some exports underline headings ("Attached unit 1" / "======", official_31).
# Only that position is decoration; a rule elsewhere still raises.
UNDERLINE_REGEX = re.compile(r"^=+$")
# The official app's footer is known by its prefix, "Exported with App Version: …",
# or the French or German one; another exporter's by naming a data version too,
# "Exported with New Recruit v37.14, Data Version: v8". Bounded, as the text is
# untrusted.
TRAILER_REGEX = re.compile(
    r"^(?:Exported with (?:App Version:|.{1,80}Data Version:)"
    r"|Exporté avec la Version de l['’]Appli|Exportiert mit App-Version)"
)
# The app's validation-error heading, followed by one bulleted line per error.
# The app upper-cases its "Errors" string, so French reads "ERREURS" and German
# "FEHLER". Matched ignoring case and a trailing colon, in case a later app
# version or a hand edit stops upper-casing it.
VALIDATION_HEADING_REGEX = re.compile(
    r"^(?:errors|erreurs|fehler)\s?:?$", re.IGNORECASE
)
# A footnote on the unit above it: "* This Datasheet also has the Battleline
# keyword" (listhammer_chaos_knights).
FOOTNOTE_REGEX = re.compile(r"^\*\s+\S")
# A header line that means to be the army size but is not POINTS_REGEX's shape:
# the size line is optional, so this one would otherwise map as a faction line.
# Leading \b and a capped run: a long digit or comma run cannot restart the scan.
LOOSE_POINTS_REGEX = re.compile(
    r"\b\d[\d,.'’\u00a0\u202f ]{0,8}\s?(?:pts?|points?|punkte)\b", re.IGNORECASE
)


class BlockKind(Enum):
    ARMY_NAME = auto()
    HEADER = auto()
    SECTION = auto()
    GROUP = auto()
    UNIT = auto()
    VALIDATION_ERRORS = auto()
    FOOTNOTE = auto()
    TRAILER = auto()


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    lines: tuple[str, ...]


def parse_points(text: str) -> int:
    """Read a POINTS_REGEX "points" group, dropping any thousands separator."""
    return int(re.sub(r"\D", "", text))


def split_blocks(text: str) -> list[list[str]]:
    """Group non-blank lines into blocks, dropping the blank separators."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip():
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def classify_blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    seen_header = False
    name_lines: list[str] = []
    for lines in split_blocks(_blank_underlines(text)):
        if not seen_header and not _is_header(lines):
            # Everything before the header is the army name: it may run over
            # several blocks ("Round 2 list", blank, "QFP (2,000 Points)") and
            # need not end in a points suffix (official_28). The blank
            # separators are kept so the name reads back verbatim.
            name_lines += [""] if name_lines else []
            name_lines += lines
            continue
        if name_lines:
            blocks.append(Block(kind=BlockKind.ARMY_NAME, lines=tuple(name_lines)))
            name_lines = []
        for block in _classify_block(lines, seen_header):
            seen_header = seen_header or block.kind is BlockKind.HEADER
            blocks.append(block)

    if not seen_header:
        # An excerpt, not the whole document: ParseError.__str__ renders the
        # block after "in block", and the full text would make that unreadable.
        first_line = text.split("\n", 1)[0]
        raise ParseError("No header block found", first_line)
    return blocks


def _blank_underlines(text: str) -> str:
    """Turn a heading's "====" underline into a blank line.

    Only the first rule after a section or group heading below the header's
    detachment line goes, even across blank lines; any other rule is left to
    raise. A blank rather than nothing, so the heading still ends its block
    when no blank line follows the underline.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    past_detachments = False
    after_heading = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if after_heading and UNDERLINE_REGEX.match(stripped):
            lines[index] = ""
            after_heading = False
            continue
        after_heading = past_detachments and (
            _is_section_heading(stripped) or _is_group_heading(stripped)
        )
        past_detachments = past_detachments or bool(DETACHMENT_REGEX.match(stripped))
    return "\n".join(lines)


def _classify_block(lines: list[str], seen_header: bool) -> list[Block]:
    """Classify one physical block, first splitting it where it fused several."""
    if not seen_header or _is_header(lines):
        head, tail = _split_header_tail(lines)
        header = Block(kind=_classify(head), lines=tuple(head))
        return [header, *(_classify_block(tail, True) if tail else [])]
    if len(lines) >= 2 and _is_fused_section_group(lines[:2]):
        return [
            Block(kind=BlockKind.SECTION, lines=(lines[0],)),
            *_classify_block(lines[1:], seen_header),
        ]
    chunks, rest = _split_fused(lines)
    return [
        *(Block(kind=_classify(chunk), lines=tuple(chunk)) for chunk in chunks),
        *(_classify_block(rest, seen_header) if rest else []),
    ]


def _split_header_tail(lines: list[str]) -> tuple[list[str], list[str]]:
    """Cut a section or group heading, and all after it, off the header block:
    New Recruit can leave out the blank line after the header too. Only lines
    after the detachment line are looked at, and only headings (an errors
    heading among them) split, since a unit header has the same shape as the
    army-size line.
    """
    detachment = next(
        (i for i, line in enumerate(lines) if DETACHMENT_REGEX.match(line.strip())),
        len(lines),
    )
    for index in range(detachment + 1, len(lines)):
        line = lines[index].strip()
        if (
            _is_section_heading(line)
            or _is_group_heading(line)
            or _is_validation_errors([line])
        ):
            return lines[:index], lines[index:]
    return lines, []


def _split_fused(lines: list[str]) -> tuple[list[list[str]], list[str]]:
    """Split a block wherever a line starts a new one: New Recruit can leave out
    the blank line after a group heading or between units.

    Margin is measured from the block's first line, so a uniformly indented
    block splits like any other. A group heading is always a lone line, so the
    line after one starts a new block whatever the body's indentation.

    An errors block is its heading plus bulleted lines, an unbulleted line
    continuing the error above it; the first line that starts a block ends it.
    The lines from there are returned unsplit, for _classify_block to classify
    afresh, since they may open with a fused section and group heading.
    """
    margin = _indent(lines[0])
    nested = any(_indent(line) > margin for line in lines)
    chunks: list[list[str]] = []
    after_group = False
    for index, line in enumerate(lines):
        if chunks and _is_validation_errors(chunks[-1]):
            if _ends_validation_errors(lines[index:], _indent(chunks[-1][0])):
                return chunks, lines[index:]
            chunks[-1].append(line)
            continue
        if (
            not chunks
            or after_group
            or (_indent(line) <= margin and _starts_block(line, nested))
        ):
            chunks.append([line])
        else:
            if not nested and _looks_like_unit_header(line):
                raise ParseError(
                    "Unit header inside a compact body; expected a blank line "
                    "before it",
                    lines,
                )
            chunks[-1].append(line)
        after_group = chunks[-1] == [line] and _is_group_heading(line.strip())
    return chunks, []


def _ends_validation_errors(rest: list[str], margin: int) -> bool:
    """Does rest[0] end the errors block above it? A bullet or a line indented
    past the heading is part of an error; any other line ends the block if it
    starts one, a title-case section heading fused onto a group heading
    included.
    """
    line = rest[0]
    if _is_bullet(line) or _indent(line) > margin:
        return False
    return _starts_block(line, nested=True) or _is_fused_section_group(rest[:2])


def _starts_block(line: str, nested: bool) -> bool:
    """Does this line, at the block's margin, begin a block of its own?

    Group headings and footers are unmistakable. A "(N Points)" line or an
    ALL-CAPS line is only structural when the body is `nested`: a compact body
    writes its run lines at the margin too, and they can have either shape.
    """
    line = line.strip()
    if _is_bullet(line):
        return False
    if _is_group_heading(line) or TRAILER_REGEX.match(line):
        return True
    return nested and (
        POINTS_REGEX.match(line) is not None or _is_section_heading(line)
    )


def _looks_like_unit_header(line: str) -> bool:
    """A compact body's run lines are "Nx" wargear, bare wargear names or
    "Keyword: …" lines, so an unbulleted "(N Points)" line that is none of
    those is a unit header with its blank line missing. It cannot be split off
    safely, but swallowing it would drop its points, so the parse fails.
    """
    line = line.strip()
    match = POINTS_REGEX.match(line)
    return (
        match is not None
        and BULLET_REGEX.match(line) is None
        and NUM_REGEX.match(line) is None
        and ":" not in match.group("name")
    )


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _is_fused_section_group(lines: list[str]) -> bool:
    """The newer dialect writes no blank line between the attached-units
    heading and the first group heading ("Attached Units" / "Attached Unit 1").
    The group line is the marker; the single line above it is a section heading
    (title-case here, so the ALL-CAPS rule cannot spot it on its own).
    """
    if len(lines) != 2:
        return False
    heading, group = (line.strip() for line in lines)
    return (
        _is_group_heading(group)
        and GROUP_REGEX.match(heading) is None
        and POINTS_REGEX.match(heading) is None
        and any(char.isalpha() for char in heading)
    )


def _classify(lines: list[str]) -> BlockKind:
    """Classify the header block or a block after it; classify_blocks has
    already folded every block before the header into the army name."""
    if TRAILER_REGEX.match(lines[0].strip()):
        return BlockKind.TRAILER

    # Ahead of the lone-line check: "ERRORS" alone would read as a section.
    if _is_validation_errors(lines):
        return BlockKind.VALIDATION_ERRORS

    if FOOTNOTE_REGEX.match(lines[0].strip()):
        return BlockKind.FOOTNOTE

    if _is_header(lines):
        return BlockKind.HEADER

    if POINTS_REGEX.match(lines[0].strip()):
        return BlockKind.UNIT

    if len(lines) == 1:
        line = lines[0].strip()
        if _is_section_heading(line):
            return BlockKind.SECTION
        if _is_group_heading(line):
            return BlockKind.GROUP
        raise ParseError("Unrecognised lone line", lines)

    raise ParseError("Unrecognised block", lines)


def _is_validation_errors(lines: list[str]) -> bool:
    return VALIDATION_HEADING_REGEX.match(lines[0].strip()) is not None


def _is_bullet(line: str) -> bool:
    return BULLET_REGEX.match(line.strip()) is not None


def _is_header(lines: list[str]) -> bool:
    return any(DETACHMENT_REGEX.match(line.strip()) for line in lines)


def _is_group_heading(line: str) -> bool:
    """The "(N Points)" suffix outranks the prefix: that line is a unit header."""
    return GROUP_REGEX.match(line) is not None and POINTS_REGEX.match(line) is None


def _is_section_heading(line: str) -> bool:
    """A section heading shouts: "ATTACHED UNITS", not "Attached unit 1"."""
    return any(char.isalpha() for char in line) and line == line.upper()
