from pathlib import Path

from listgrok import ParseError, parse_list

EXAMPLE_DIRS = ("official_app", "new_recruit/wtc")


def parse_examples():
    for directory in EXAMPLE_DIRS:
        root_dir = Path(__file__).parent / directory
        for file in sorted(root_dir.iterdir()):
            if file.suffix != ".txt":
                continue
            try:
                army_list = parse_list(file.read_text())
            except ParseError as error:
                # lvo2026_genestealer_cults is hand-annotated and does not parse.
                print(f"Failed {directory}/{file.name}: {error}\n\n")
                continue
            print(f"Parsed {directory}/{file.name}: {army_list.name}")
            print(army_list)
            print("\n\n")


if __name__ == "__main__":
    parse_examples()
