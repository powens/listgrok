from listgrok.army.army_list import ArmyList
from listgrok.parsers.new_recruit_gw import NewRecruitGWParser


def parse_list(list_text: str) -> ArmyList:
    return NewRecruitGWParser().parse(list_text)
