# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-10-28

### Fixed

- Detachment lines joined by a bare "and" (`A and B`) are split into separate
  detachments; detachment names that themselves contain a joiner (e.g.
  `Legends of Saga and Song`, `Ordo Xenos, Alien Hunters`) are kept whole.
- Army names containing a blank line no longer fail to parse.
- Exports from app v2.6.0 (144), which out-dent `Attached as:` and continue
  bulleted lists with unbulleted lines, now parse with the correct nesting.
- A trailing space no longer ends up on the army name when the export puts two
  spaces before its `(N Points)` suffix.
- Unit bodies that lost their indentation but keep their `•`/`◦` bullets no
  longer have wargear misread as model sets.

## [0.1.0] - 2026-07-31

### Added

- `parse_list()` parses Warhammer 40k 11th edition army lists exported from
  the official app — both the classic and compact export dialects — into a
  common data model.
- Data model dataclasses: `ArmyList`, `Unit`, `UnitComposition`, `Attachment`,
  each with a stable-keyed `to_dict()`.
- `ParseError` raised on input the parser does not understand, rather than
  returning a half-filled `ArmyList`.
- Fully typed package (`py.typed`), zero runtime dependencies,
  Python 3.10–3.14.

[Unreleased]: https://github.com/powens/listgrok/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/powens/listgrok/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/powens/listgrok/releases/tag/v0.1.0
