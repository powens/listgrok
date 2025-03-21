# import argparse
from listgrok import parse_list


if __name__ == "__main__":
    with open("examples/official_app/example1.txt", "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list)

    with open("examples/official_app/example2.txt", "r") as f:
        list_text = f.read()
    list = parse_list(list_text)
    print(list)

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