from listgrok.parsers.official_app import OfficialAppListParser
from listgrok.army.army_list import ArmyList


def parse_list(list: str) -> ArmyList:
    return OfficialAppListParser().parse_list(list)
