# listgrok

**NOTE** listgrok is still in early development. The APIs are unstable and very few features are implemented

## Description

listgrok is a library for parsing Warhammer 40k army lists.

## Supported formats

- [x] Official GW 40k app
- [ ] NewRecruit:
  - [x] GW format
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
Boop (1985 Points)

Space Marines
Space Wolves
Stormlance Task Force
Strike Force (2000 Points)

CHARACTERS

Bjorn the Fell-Handed (190 Points)
  • 1x Heavy flamer
  • 1x Helfrost cannon
  • 1x Trueclaw
"""

list = parse_list(my_list_text)
```

## Contributing

Contributions are welcome! If you would like to contribute to this project, please follow the guidelines in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the [MIT License](LICENSE).
