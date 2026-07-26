# import argparse
from listgrok import parse_list
from pathlib import Path


def official_app():
    root_dir = Path("examples/official_app")
    for file in root_dir.iterdir():
        if file.suffix != ".txt":
            continue
        with open(file, "r") as f:
            list_text = f.read()
        army_list = parse_list(list_text)
        print(f"Parsed {file.name}: {army_list.name}")
        print(army_list)
        print("\n\n")


if __name__ == "__main__":
    official_app()

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
