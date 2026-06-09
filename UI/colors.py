from enum import IntEnum


class Color(IntEnum):
    BLACK = 0
    DARK_BLUE = 1
    DARK_GREEN = 2
    DARK_CYAN = 3
    DARK_RED = 4
    DARK_MAGENTA = 5
    DARK_YELLOW = 6
    GRAY = 7
    DARK_GRAY = 8
    BLUE = 9
    GREEN = 10
    CYAN = 11
    RED = 12
    MAGENTA = 13
    YELLOW = 14
    WHITE = 15


_ANSI = {
    Color.BLACK: 30,
    Color.DARK_BLUE: 34,
    Color.DARK_GREEN: 32,
    Color.DARK_CYAN: 36,
    Color.DARK_RED: 31,
    Color.DARK_MAGENTA: 35,
    Color.DARK_YELLOW: 33,
    Color.GRAY: 37,
    Color.DARK_GRAY: 90,
    Color.BLUE: 94,
    Color.GREEN: 92,
    Color.CYAN: 96,
    Color.RED: 91,
    Color.MAGENTA: 95,
    Color.YELLOW: 93,
    Color.WHITE: 97,
}


def ansi_fg(color: Color) -> str:
    return f"\033[{_ANSI[color]}m"


RESET = "\033[0m"


# Pygame RGB color definitions
_RGB = {
    Color.BLACK: (12, 12, 16),
    Color.DARK_BLUE: (24, 32, 60),      # Wall explored/dim
    Color.DARK_GREEN: (20, 50, 25),     # Dark forest/nature
    Color.DARK_CYAN: (24, 75, 80),      # Wall visible
    Color.DARK_RED: (120, 30, 30),      # Threat warning
    Color.DARK_MAGENTA: (80, 25, 80),
    Color.DARK_YELLOW: (110, 85, 30),   # Floor visible
    Color.GRAY: (140, 140, 145),        # Explorers, key labels
    Color.DARK_GRAY: (45, 45, 50),      # Floor explored/dim
    Color.BLUE: (60, 120, 240),
    Color.GREEN: (46, 196, 120),        # High-health/Heal/Success
    Color.CYAN: (45, 175, 205),         # Items/pickup alerts
    Color.RED: (210, 55, 55),           # Low HP/Damage
    Color.MAGENTA: (200, 60, 200),      # Magic/Zaps
    Color.YELLOW: (235, 195, 45),       # Highlights/stairs
    Color.WHITE: (230, 230, 235),       # Player/Text
}


def color_rgb(color: Color) -> tuple[int, int, int]:
    return _RGB.get(color, (140, 140, 145))

