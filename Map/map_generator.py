import random
from dataclasses import dataclass

from Entities import monster_factory
from Items import item as item_factory
from Map.dungeon_level import DungeonLevel
from Map.tile import TileType


@dataclass(frozen=True)
class _Room:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def intersects(self, other: "_Room") -> bool:
        return (
            self.x <= other.x + other.width
            and self.x + self.width >= other.x
            and self.y <= other.y + other.height
            and self.y + self.height >= other.y
        )

    def random_point(self, rng: random.Random) -> tuple[int, int]:
        return (
            rng.randrange(self.x + 1, self.x + self.width - 1),
            rng.randrange(self.y + 1, self.y + self.height - 1),
        )


class MapGenerator:
    def __init__(self, rng: random.Random):
        self._rng = rng

    def generate(self, width: int, height: int, depth: int, allow_boss_spawn: bool) -> DungeonLevel:
        level = DungeonLevel(width, height)
        rooms: list[_Room] = []
        max_attempts = 30
        min_size = 4
        max_size = 9

        for _ in range(max_attempts):
            w = self._rng.randrange(min_size, max_size + 1)
            h = self._rng.randrange(min_size, max_size + 1)
            x = self._rng.randrange(1, width - w - 1)
            y = self._rng.randrange(1, height - h - 1)
            room = _Room(x, y, w, h)

            if any(room.intersects(other) for other in rooms):
                continue

            self._carve_room(level, room)
            if rooms:
                px, py = rooms[-1].center
                cx, cy = room.center
                if self._rng.randrange(2) == 0:
                    self._carve_h_tunnel(level, px, cx, py)
                    self._carve_v_tunnel(level, py, cy, cx)
                else:
                    self._carve_v_tunnel(level, py, cy, px)
                    self._carve_h_tunnel(level, px, cx, cy)
            rooms.append(room)

        level.player_spawn = rooms[0].center

        stairs = rooms[-1].center
        level.tiles[stairs[0]][stairs[1]].type = TileType.STAIRS_DOWN
        level.stairs_down = stairs

        if depth > 1:
            stairs_up = rooms[0].center
            level.tiles[stairs_up[0]][stairs_up[1]].type = TileType.STAIRS_UP
            level.stairs_up = stairs_up
            level.has_stairs_up = True

        should_spawn_boss = allow_boss_spawn and depth > 3 and self._rng.randrange(100) < 15
        if should_spawn_boss and len(rooms) > 1:
            room_index = self._rng.randrange(1, len(rooms))
            bx, by = rooms[room_index].random_point(self._rng)
            level.monsters.append(monster_factory.create_boss(bx, by))

        for i in range(1, len(rooms)):
            if self._rng.randrange(100) < 20:
                fx, fy = rooms[i].random_point(self._rng)
                if (fx, fy) != stairs:
                    level.tiles[fx][fy].type = TileType.FOUNTAIN

            monster_count = self._rng.randrange(0, 2 + depth // 2)
            for _ in range(monster_count):
                mx, my = rooms[i].random_point(self._rng)
                if level.monster_at(mx, my) is None and (mx, my) != stairs:
                    level.monsters.append(monster_factory.create(mx, my, depth, self._rng))
            if self._rng.randrange(100) < 60:
                ix, iy = rooms[i].random_point(self._rng)
                if level.item_at(ix, iy) is None:
                    level.items.append(item_factory.create(ix, iy, depth, self._rng))
            if self._rng.randrange(100) < 20:
                ix, iy = rooms[i].random_point(self._rng)
                if level.item_at(ix, iy) is None:
                    level.items.append(item_factory.create(ix, iy, depth, self._rng))

        return level

    @staticmethod
    def _carve_room(level: DungeonLevel, room: _Room):
        for x in range(room.x, room.x + room.width):
            for y in range(room.y, room.y + room.height):
                level.tiles[x][y].type = TileType.FLOOR

    @staticmethod
    def _carve_h_tunnel(level: DungeonLevel, x1: int, x2: int, y: int):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            level.tiles[x][y].type = TileType.FLOOR

    @staticmethod
    def _carve_v_tunnel(level: DungeonLevel, y1: int, y2: int, x: int):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            level.tiles[x][y].type = TileType.FLOOR
