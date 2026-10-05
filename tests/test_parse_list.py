from pathlib import Path

import pytest

from listgrok import ParseError, parse_list

EXAMPLES = Path(__file__).parents[1] / "examples"


def test_official_app_export_routes_to_the_official_app_parser():
    army_list = parse_list((EXAMPLES / "official_app" / "official_1.txt").read_text())

    assert army_list.faction == "T’au Empire"
    assert army_list.disposition == "Purge the Foe"


def test_new_recruit_wtc_export_routes_to_the_wtc_parser():
    text = (EXAMPLES / "new_recruit" / "wtc" / "nr_wtc_0.txt").read_text()
    army_list = parse_list(text)

    assert army_list.faction == "Adeptus Custodes"
    assert army_list.detachments == ["Lions of the Emperor"]


def test_unrecognised_export_raises_naming_every_parser():
    # No parser absorbs this, so the failure must surface — with each
    # parser's reason, so a near-miss is diagnosable.
    with pytest.raises(ParseError) as raised:
        parse_list("Just some notes about my army\n")

    message = str(raised.value)
    assert "official app:" in message
    assert "New Recruit WTC:" in message
