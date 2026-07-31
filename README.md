# listgrok

**NOTE** listgrok is still in early development. The APIs are unstable and very few features are implemented

## Description

listgrok is a zero-dependency library that parses Warhammer 40k army lists into a common data model of plain dataclasses, ready for JSON via `to_dict()`.

## Installation

```sh
pip install listgrok
```

listgrok has no runtime dependencies and supports Python 3.10 and newer.

## Supported formats

- [x] Official GW 40k app (11th edition)

Planned:

- [ ] NewRecruit:
  - [ ] GW format
  - [ ] Markdown format
  - [ ] WTC
  - [ ] WTC-short
- [ ] Battlescribe

## Usage

`parse_list` returns an `ArmyList`. Input it does not understand raises `ParseError` rather than returning a half-filled list.

```python
from listgrok import ParseError, parse_list

my_list_text = """
11th stuff (2,000 Points)

T’au Empire
Retaliation Cadre (3 Detachment Points)
Purge the Foe
Strike Force (2,000 Points)

ATTACHED UNITS

Attached unit 1

Commander Farsight (70 Points)
  • Attached as: Leader (Character)
  • 1x Dawn Blade

Crisis Sunforge Battlesuits (125 Points)
  • Attached as: Bodyguard ()
  • 1x Crisis Sunforge Shas’vre
     ◦ 1x Battlesuit fists
"""

try:
    army_list = parse_list(my_list_text)
except ParseError as err:
    print(f"Not a recognised army list: {err}")
else:
    print(army_list.name)  # "11th stuff"
    data = army_list.to_dict()  # JSON-ready dict with stable keys
```

## Contributing

Contributions are welcome! If you would like to contribute to this project, please follow the guidelines in [CONTRIBUTING.md](https://github.com/powens/listgrok/blob/main/CONTRIBUTING.md).

## License

This project is licensed under the [MIT License](https://github.com/powens/listgrok/blob/main/LICENSE).
