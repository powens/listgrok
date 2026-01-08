# import argparse
from listgrok import parse_list
from pathlib import Path


def official_app():
    with open(Path("official_app/example1.txt"), "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list.name)
    print(list)

    print("\n\n")

    with open(Path("official_app/example2.txt"), "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list.name)
    print(list)


def new_recruit():
    from listgrok.parsers.new_recruit_gw import NewRecruitGWParser

    with open(Path("examples/nr/nr1_gw.txt"), "r") as f:
        list_text = f.read()
    list = NewRecruitGWParser().parse(list_text)
    print(list.name)
    print(list)


if __name__ == "__main__":
    official_app()
    new_recruit()

    # parser = argparse.ArgumentParser(description="Parse army lists from a file or stdin.")
    # parser.add_argument(
    #     "input",
    #     nargs="?",
    #     type=argparse.FileType("r"),
    #     default="-",
    #     help="Input file to parse (default: stdin)",
    # )
    # args = parser.parse_args()

    # list_text = args.input.read()
    # args.input.close()
    # list = parse_list(list_text)
    # print(list)
