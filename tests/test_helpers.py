import pytest
from listgrok.parsers.helpers import count_leading_spaces

@pytest.mark.parametrize(
    "line,expected",
    [
        ("foo", 0),
        ("  • 1x Dawn Blade", 2),
        ("     ◦ 1x Marksman bolt carbine", 5),
        ("• 1x Kroot Carnivore", 0),
        ("    • 1x Close combat weapon", 4),
    ],
)
def test_count_leading_spaces(line, expected):
    assert count_leading_spaces(line) == expected