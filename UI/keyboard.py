KEY_UP = "UP"
KEY_DOWN = "DOWN"
KEY_LEFT = "LEFT"
KEY_RIGHT = "RIGHT"


class RawTerminal:
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def read_key() -> str:
    # Deprecated for Pygame, stubbed to prevent import failures
    return ""
