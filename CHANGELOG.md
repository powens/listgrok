# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `parse_list()` also parses New Recruit's WTC-format export, falling back to
  it when the official-app parser rejects the input. Leader/bodyguard pairs
  become `Attachment` groups named `Attached unit N`.

### Changed

- When no parser understands the input, the `ParseError` message names each
  parser's reason.

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
