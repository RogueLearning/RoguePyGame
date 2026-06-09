import math

from Map.dungeon_level import DungeonLevel


def compute(level: DungeonLevel, px: int, py: int, radius: int):
    level.reset_visibility()
    if not level.in_bounds(px, py):
        return
    level.tiles[px][py].visible = True
    level.tiles[px][py].explored = True

    rays = 360
    for i in range(rays):
        angle = (i * math.pi * 2.0) / rays
        dx = math.cos(angle)
        dy = math.sin(angle)
        x = px + 0.5
        y = py + 0.5
        for _ in range(radius):
            x += dx
            y += dy
            ix = int(x)
            iy = int(y)
            if not level.in_bounds(ix, iy):
                break
            tile = level.tiles[ix][iy]
            tile.visible = True
            tile.explored = True
            if tile.blocks_sight:
                break
