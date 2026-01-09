from listgrok.parsers.official_app import parse_official_app
from listgrok.parsers.new_recruit_gw import NewRecruitGWParser
from listgrok.parsers.parse_error import ParseError
from listgrok.army.army_list import ArmyList


def parse_list(list: str) -> ArmyList:
    try:
        return parse_official_app(list)
    except ParseError:
        return NewRecruitGWParser().parse(list)
