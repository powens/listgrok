from listgrok.parsers.official_app import OfficialAppParser
from listgrok.army.army_list import ArmyList


def parse_list(list: str) -> ArmyList:
    return OfficialAppParser().parse(list)
