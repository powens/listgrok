from listgrok.exceptions import ParseError
from listgrok.models import ArmyList
from listgrok.parsers import parse_new_recruit_wtc, parse_official_app

# Tried in order; the first that does not raise ParseError wins. Detection is by
# attempted parse, never by sniffing — so each parser must raise on input it
# does not understand rather than return a half-filled ArmyList.
_PARSERS = (
    ("official app", parse_official_app),
    ("New Recruit WTC", parse_new_recruit_wtc),
)


def parse_list(list_text: str) -> ArmyList:
    """Parse an army list export into an `ArmyList`.

    Supports the official 40k app's 11th edition export, New Recruit's export
    of the same layout, and New Recruit's WTC export. Input no parser
    understands raises `ParseError` naming each parser's reason, rather than
    returning a half-filled `ArmyList`.
    """
    errors: list[tuple[str, ParseError]] = []
    for label, parser in _PARSERS:
        try:
            return parser(list_text)
        except ParseError as error:
            errors.append((label, error))
    reasons = "; ".join(f"{label}: {error}" for label, error in errors)
    # Chained from the first parser's error, so its `message` and `block` stay
    # reachable as `__cause__`; the message names every parser's reason.
    raise ParseError("Unrecognised army list; " + reasons) from errors[0][1]
