# import argparse
from listgrok import parse_list


def official_app():
    with open("examples/official_app/example1.txt", "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list.name)
    print(list)

    print("\n\n")

    with open("examples/official_app/example2.txt", "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list.name)
    print(list)


def new_recruit():
    from listgrok.parsers.new_recruit import NewRecruitParser
    with open("examples/nr/nr1_gw.txt", "r") as f:
        list_text = f.read()
    list = NewRecruitParser().parse(list_text)
    print(list.name)
    print(list)

if __name__ == "__main__":
    # official_app()
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