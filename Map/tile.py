from enum import Enum


class TileType(Enum):
    WALL = "wall"
    FLOOR = "floor"
    STAIRS_DOWN = "stairs_down"
    STAIRS_UP = "stairs_up"
    FOUNTAIN = "fountain"


class Tile:
    __slots__ = ("type", "visible", "explored")

    def __init__(self, type: TileType = TileType.WALL):
        self.type = type
        self.visible = False
        self.explored = False

    @property
    def is_walkable(self) -> bool:
        return self.type != TileType.WALL

    @property
    def blocks_sight(self) -> bool:
        return self.type == TileType.WALL
