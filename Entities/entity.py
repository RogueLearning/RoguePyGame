from UI.colors import Color


class Entity:
    def __init__(self):
        self.x: int = 0
        self.y: int = 0
        self.glyph: str = "??"
        self.color: Color = Color.GRAY
        self.name: str = ""
