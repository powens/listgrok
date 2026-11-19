from pathlib import Path

from listgrok import ParseError, parse_list


def official_app():
    root_dir = Path(__file__).parent / "official_app"
    for file in root_dir.iterdir():
        if file.suffix != ".txt":
            continue
        try:
            army_list = parse_list(file.read_text())
        except ParseError as error:
            # lvo2026_genestealer_cults is hand-annotated and does not parse.
            print(f"Failed {file.name}: {error}\n\n")
            continue
        print(f"Parsed {file.name}: {army_list.name}")
        print(army_list)
        print("\n\n")


if __name__ == "__main__":
    official_app()
