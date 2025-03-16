class ParseError(Exception):
    def __init__(self, message: str, line: str):
        self.message = message
        self.line = line

    def __str__(self):
        return f"ParseError: {self.message} on line {self.line}"
