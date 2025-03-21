class ParseError(Exception):
    def __init__(self, message: str, block: str | list[str]):
        self.message = message
        self.block = block

    def __str__(self):
        return f"ParseError: {self.message} on line {self.block}"
