import re
from enum import Enum, auto

# re.DOTALL because some army names span multiple lines. It is harmless for
# single-line matches, so one pattern serves both unit headers and army names.
POINTS_LABEL_REGEX = re.compile(
    r"^(?P<name>.+)\s\((?P<points>\d+)\s[Pp]oints\)$", re.DOTALL
)
NUM_REGEX = re.compile(r"^(?P<num>\d+)x\s(?P<name>.*)$")
UNIT_TYPES = frozenset(
    {
        "CHARACTERS",
        "OTHER DATASHEETS",
        "ALLIED UNITS",
        "BATTLELINE",
        "DEDICATED TRANSPORTS",
    }
)


class ParserStage(Enum):
    START = auto()
    FACTION = auto()
    UNIT_DETAILS = auto()


def count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip())


def count_leading_hashes(line: str) -> int:
    return len(line) - len(line.lstrip("#"))
