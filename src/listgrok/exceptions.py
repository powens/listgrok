from collections.abc import Sequence


class ParseError(Exception):
    """Raised when input text cannot be parsed as a known army-list format."""

    def __init__(self, message: str, block: str | Sequence[str] = ""):
        # Both args go to Exception so pickle can reconstruct via Cls(*args).
        super().__init__(message, block)
        self.message = message
        self.block = block

    def __str__(self) -> str:
        if not self.block:
            return self.message
        return f"{self.message} in block {self.block!r}"
