def count_leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip())