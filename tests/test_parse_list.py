from pathlib import Path

import pytest

from listgrok import ParseError, parse_list

EXAMPLES = Path(__file__).parents[1] / "examples"


def test_official_app_export_routes_to_the_official_app_parser():
    army_list = parse_list((EXAMPLES / "official_app" / "official_11.txt").read_text())

    assert army_list.faction == "Astra Militarum"
    assert army_list.disposition == "Take and Hold"


def test_unrecognised_export_raises_rather_than_returning_a_partial_list():
    # There is no fallback parser to absorb this, so the failure must surface.
    with pytest.raises(ParseError):
        parse_list("+ FACTION KEYWORD: Xenos - T’au Empire\n")
