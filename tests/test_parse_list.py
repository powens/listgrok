from pathlib import Path

import pytest

from listgrok import parse_list
from listgrok.parsers.parse_error import ParseError

EXAMPLES = Path(__file__).parents[1] / "examples"


def test_official_app_export_routes_to_the_official_app_parser():
    army_list = parse_list((EXAMPLES / "official_app" / "official_1.txt").read_text())

    assert army_list.faction == "T’au Empire"
    assert army_list.disposition == "Purge the Foe"


def test_unrecognised_export_raises_rather_than_returning_a_partial_list():
    # There is no fallback parser to absorb this, so the failure must surface.
    with pytest.raises(ParseError):
        parse_list("+ FACTION KEYWORD: Xenos - T’au Empire\n")
