# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Official-app exports with notes around the army name — before it, after
  it, or with no army name at all — now parse; the notes are dropped instead
  of raising `ParseError`.
- Official-app exports that nest wargear under column-zero `◦` sub-bullets
  (some app v2.6.0 (3) exports) no longer read each weapon as its own model
  set.
- An `Enhancement:` line ending a compact-dialect unit body is now read as
  the unit's enhancement instead of a decoration.

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

[Unreleased]: https://github.com/powens/listgrok/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/powens/listgrok/releases/tag/v0.1.0
