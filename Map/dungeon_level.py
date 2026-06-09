from Entities.monster import Monster
from Items.item import ItemEntity
from Map.tile import Tile, TileType


class DungeonLevel:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles: list[list[Tile]] = [
            [Tile(TileType.WALL) for _ in range(height)] for _ in range(width)
        ]
        self.monsters: list[Monster] = []
        self.items: list[ItemEntity] = []
        self.stairs_down: tuple[int, int] = (0, 0)
        self.stairs_up: tuple[int, int] = (0, 0)
        self.has_stairs_up: bool = False
        self.player_spawn: tuple[int, int] = (0, 0)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.tiles[x][y].is_walkable

    def monster_at(self, x: int, y: int) -> Monster | None:
        for m in self.monsters:
            if m.is_alive and m.x == x and m.y == y:
                return m
        return None

    def item_at(self, x: int, y: int) -> ItemEntity | None:
        for i in self.items:
            if i.x == x and i.y == y:
                return i
        return None

    def reset_visibility(self):
        for col in self.tiles:
            for t in col:
                t.visible = False
