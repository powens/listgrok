from pathlib import Path

from listgrok import parse_list

EXAMPLES = Path(__file__).parents[2] / "examples"


def test_official_app_export_routes_to_the_official_app_parser():
    army_list = parse_list((EXAMPLES / "official_app" / "official_1.txt").read_text())

    assert army_list.faction == "T’au Empire"
    assert army_list.disposition == "Purge the Foe"


def test_new_recruit_export_falls_back_to_the_new_recruit_parser():
    army_list = parse_list((EXAMPLES / "nr" / "nr1_gw.txt").read_text())

    # Note the plain ASCII apostrophe: the NewRecruit fixture uses U+0027 where
    # the official-app fixtures use the typographic U+2019.
    assert army_list.faction == "Xenos - T'au Empire"
    assert army_list.detachments == ["Experimental Prototype Cadre"]
    assert army_list.disposition == ""
