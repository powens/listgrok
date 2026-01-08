def count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip())


def count_leading_hashes(line: str) -> int:
    return len(line) - len(line.lstrip("#"))
