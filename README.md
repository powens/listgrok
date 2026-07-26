# listgrok

**NOTE** listgrok is still in early development. The APIs are unstable and very few features are implemented

## Description

listgrok is a library for parsing Warhammer 40k army lists.

## Supported formats

- [x] Official GW 40k app (11th edition)
- [ ] NewRecruit:
  - [ ] GW format
  - [ ] Markdown format
  - [ ] WTC
  - [ ] WTC-short

## Features

- Parse lists from:
  - Official 40k app
  - NewRecruit formats
  - Battlescribe format
- Output to a common json (or yaml?) format

## Usage

```python
from listgrok import parse_list

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

army_list = parse_list(my_list_text)
```

## Contributing

Contributions are welcome! If you would like to contribute to this project, please follow the guidelines in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the [MIT License](LICENSE).
