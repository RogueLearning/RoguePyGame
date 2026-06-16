from enum import Enum


class TileType(Enum):
    WALL = "wall"
    FLOOR = "floor"
    STAIRS_DOWN = "stairs_down"
    STAIRS_UP = "stairs_up"
    FOUNTAIN = "fountain"
    CHASM = "chasm"


class Tile:
    __slots__ = ("type", "visible", "explored")

    def __init__(self, type: TileType = TileType.WALL):
        self.type = type
        self.visible = False
        self.explored = False

    @property
    def is_walkable(self) -> bool:
        # Chasms are open gaps -- you can't walk across without a grappling hook.
        return self.type not in (TileType.WALL, TileType.CHASM)

    @property
    def blocks_sight(self) -> bool:
        # You can see across a chasm; only walls block line of sight.
        return self.type == TileType.WALL
