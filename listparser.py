from typing import List
from listgrok.parsers.official_app import ListParser


def parse_wh_app_list(list_text: str) -> List:
    return ListParser().parse_list(list_text)


def parse_list(list: str) -> List:
    return parse_wh_app_list(list)


if __name__ == "__main__":
    with open("examples/example1.txt", "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list)

    with open("examples/example2.txt", "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list)
