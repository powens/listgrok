from listgrok.army.army_list import ArmyList
from listgrok.parsers.new_recruit_gw import NewRecruitGWParser
from listgrok.parsers.official_app import parse_official_app
from listgrok.parsers.parse_error import ParseError


def parse_list(list_text: str) -> ArmyList:
    try:
        return parse_official_app(list_text)
    except ParseError:
        return NewRecruitGWParser().parse(list_text)
