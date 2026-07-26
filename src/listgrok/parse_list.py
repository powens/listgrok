from listgrok.army.army_list import ArmyList
from listgrok.parsers.official_app import parse_official_app


def parse_list(list_text: str) -> ArmyList:
    """Parse an army list export into an `ArmyList`.

    Only the official 40k app's 11th edition export is supported. Anything else
    raises `ParseError` rather than returning a half-filled `ArmyList`.
    """
    return parse_official_app(list_text)
