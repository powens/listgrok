from pathlib import Path

from listgrok import parse_list


def official_app():
    root_dir = Path(__file__).parent / "official_app"
    for file in root_dir.iterdir():
        if file.suffix != ".txt":
            continue
        army_list = parse_list(file.read_text())
        print(f"Parsed {file.name}: {army_list.name}")
        print(army_list)
        print("\n\n")


if __name__ == "__main__":
    official_app()
