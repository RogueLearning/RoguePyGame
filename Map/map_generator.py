import random
from dataclasses import dataclass

from Entities import monster_factory
from Items import item as item_factory
from Map.dungeon_level import DungeonLevel
from Map.tile import TileType

# The overworld is a large, scrolling, procedurally generated map (roughly 10x
# the area of a dungeon floor). The renderer follows the player with a camera.
OVERWORLD_WIDTH = 90
OVERWORLD_HEIGHT = 60

# Each dungeon is this many floors deep; the last floor is the boss lair.
DUNGEON_DEPTH = 5

_VILLAGER_LINES = [
    "Welcome, traveler! Three dungeons lie hidden across these lands.",
    "Press [I] to manage your gear before heading underground.",
    "The Knight blocks 1 damage from every monster hit.",
    "Rest at a glowing fountain to restore your health.",
]
_FARMER_LINES = [
    "The cellar to the north is crawling with giant rats... and worse.",
    "Some chests aren't chests at all. Watch for Mimics!",
    "A Rogue strikes for double damage 30% of the time.",
    "A merchant wanders the depths, trading wares for gold.",
]
_GHOST_LINES = [
    "Boooo... only kidding. The crypt lies somewhere in this graveyard.",
    "Locked chests need a key - it's always hidden on the same floor.",
    "Only enchanted steel can wound the dungeon bosses.",
    "Wizards slowly recharge their wand over time.",
]
_DRUID_LINES = [
    "A dark cave opens somewhere in these wild fields.",
    "Equip a bow and arrows to strike foes from afar.",
    "Witches hurl fireballs and trolls loose arrows - keep moving!",
    "Press [Enter] on a portal to enter or leave a dungeon.",
]


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

    def generate(self, width: int, height: int, depth: int, allow_boss_spawn: bool,
                 dungeon_id: str = "") -> DungeonLevel:
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

        # The final floor of a dungeon is the boss lair: no stairs down, and a
        # unique boss guards it. Earlier floors descend normally.
        is_boss_floor = dungeon_id != "" and depth >= DUNGEON_DEPTH
        stairs = rooms[-1].center
        if is_boss_floor:
            bx, by = stairs
            level.stairs_down = stairs  # kept for reference; tile stays FLOOR
            level.monsters.append(monster_factory.create_dungeon_boss(dungeon_id, bx, by))
        else:
            level.tiles[stairs[0]][stairs[1]].type = TileType.STAIRS_DOWN
            level.stairs_down = stairs

        if depth >= 1:
            stairs_up = rooms[0].center
            level.tiles[stairs_up[0]][stairs_up[1]].type = TileType.STAIRS_UP
            level.stairs_up = stairs_up
            level.has_stairs_up = True

        # Spawn merchant with 50% chance on depth >= 2
        if depth >= 2 and self._rng.randrange(100) < 50 and len(rooms) > 1:
            from Entities.merchant import Merchant
            room_idx = self._rng.randrange(1, len(rooms))
            mx, my = rooms[room_idx].random_point(self._rng)
            attempts = 0
            while (level.monster_at(mx, my) is not None or (mx, my) == stairs) and attempts < 10:
                mx, my = rooms[room_idx].random_point(self._rng)
                attempts += 1
            merchant = Merchant(depth, self._rng)
            merchant.x = mx
            merchant.y = my
            level.monsters.append(merchant)

        spawn_key = False
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

            # Spawn chests (20% normal, 15% locked, 10% mimic)
            roll = self._rng.randrange(100)
            if roll < 15:
                cx, cy = rooms[i].random_point(self._rng)
                if level.monster_at(cx, cy) is None and (cx, cy) != stairs:
                    from Entities.chest import Chest
                    chest = Chest(is_locked=True, is_mimic=False, depth=depth, rng=self._rng)
                    chest.x = cx
                    chest.y = cy
                    level.monsters.append(chest)
                    spawn_key = True
            elif roll < 35:
                cx, cy = rooms[i].random_point(self._rng)
                if level.monster_at(cx, cy) is None and (cx, cy) != stairs:
                    from Entities.chest import Chest
                    chest = Chest(is_locked=False, is_mimic=False, depth=depth, rng=self._rng)
                    chest.x = cx
                    chest.y = cy
                    level.monsters.append(chest)
            elif roll < 45:
                cx, cy = rooms[i].random_point(self._rng)
                if level.monster_at(cx, cy) is None and (cx, cy) != stairs:
                    from Entities.chest import Chest
                    chest = Chest(is_locked=False, is_mimic=True, depth=depth, rng=self._rng)
                    chest.x = cx
                    chest.y = cy
                    level.monsters.append(chest)

        if spawn_key:
            key_placed = False
            for attempts in range(50):
                room_idx = self._rng.randrange(1, len(rooms))
                kx, ky = rooms[room_idx].random_point(self._rng)
                if level.item_at(kx, ky) is None and level.monster_at(kx, ky) is None and (kx, ky) != stairs:
                    from Items.item import create_key
                    level.items.append(create_key(kx, ky))
                    key_placed = True
                    break
            if not key_placed:
                kx, ky = rooms[0].random_point(self._rng)
                if level.item_at(kx, ky) is None:
                    from Items.item import create_key
                    level.items.append(create_key(kx, ky))

        # Carve chasms (open gaps you need a grappling hook to cross).
        self._carve_chasms(level, rooms, stairs)

        return level

    def _carve_chasms(self, level: DungeonLevel, rooms, stairs_down):
        """Add a few chasm pools inside non-critical rooms. Always verifies the
        stairs stay reachable on foot, so a level is never made unwinnable --
        the hook only ever opens shortcuts and chasm-locked loot."""
        rng = self._rng
        if len(rooms) < 3 or rng.randrange(100) >= 60:
            return

        protected = {r.center for r in rooms}
        protected.add(stairs_down)

        changed = []
        for _ in range(rng.randint(1, 2)):
            idx = rng.randint(1, len(rooms) - 2)  # not spawn room, not stairs room
            room = rooms[idx]
            for (cx, cy) in self._grow_blob(room, rng.randint(3, 7), protected):
                t = level.tiles[cx][cy]
                if (t.type == TileType.FLOOR and (cx, cy) not in protected
                        and level.monster_at(cx, cy) is None
                        and level.item_at(cx, cy) is None):
                    t.type = TileType.CHASM
                    changed.append((cx, cy))

        # Revert everything if the stairs can no longer be walked to.
        if changed and not self._reachable(level, level.player_spawn, stairs_down):
            for (cx, cy) in changed:
                level.tiles[cx][cy].type = TileType.FLOOR

    def _grow_blob(self, room: "_Room", size: int, protected) -> set:
        """Random-walk a small blob of cells inside a room's interior."""
        rng = self._rng
        ix0, iy0 = room.x + 1, room.y + 1
        ix1, iy1 = room.x + room.width - 2, room.y + room.height - 2
        if ix1 < ix0 or iy1 < iy0:
            return set()
        sx, sy = rng.randint(ix0, ix1), rng.randint(iy0, iy1)
        cells, cur = set(), (sx, sy)
        for _ in range(size * 3):
            if len(cells) >= size:
                break
            cx, cy = cur
            if (cx, cy) not in protected:
                cells.add((cx, cy))
            dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            ncx, ncy = cx + dx, cy + dy
            cur = (ncx, ncy) if (ix0 <= ncx <= ix1 and iy0 <= ncy <= iy1) else (sx, sy)
        return cells

    @staticmethod
    def _reachable(level: DungeonLevel, start, target) -> bool:
        from collections import deque
        seen = {start}
        q = deque([start])
        while q:
            x, y = q.popleft()
            if (x, y) == target:
                return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if level.is_walkable(nx, ny) and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))
        return target in seen

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

    def generate_overworld(self) -> DungeonLevel:
        rng = self._rng
        W, H = OVERWORLD_WIDTH, OVERWORLD_HEIGHT
        level = DungeonLevel(W, H)
        level.is_overworld = True

        # Base terrain is open, walkable ground everywhere...
        for x in range(W):
            for y in range(H):
                level.tiles[x][y].type = TileType.FLOOR
        # ...ringed by a solid border so you can't walk off the world.
        for x in range(W):
            level.tiles[x][0].type = TileType.WALL
            level.tiles[x][H - 1].type = TileType.WALL
        for y in range(H):
            level.tiles[0][y].type = TileType.WALL
            level.tiles[W - 1][y].type = TileType.WALL

        # Four biome quadrants (matched by the renderer): town TL, farm TR,
        # cemetery BL, field BR. Each is a region rect inset from the border.
        hw, hh = W // 2, H // 2
        town = (2, 2, hw - 2, hh - 2)
        farm = (hw + 1, 2, W - 3, hh - 2)
        cemetery = (2, hh + 1, hw - 2, H - 3)
        field = (hw + 1, hh + 1, W - 3, H - 3)

        # Procedurally scatter structures + obstacles per biome.
        self._scatter_houses(level, town, count=8, min_s=5, max_s=8)
        self._scatter_houses(level, farm, count=3, min_s=6, max_s=9)
        self._scatter_fences(level, farm, count=5)
        self._scatter_houses(level, cemetery, count=2, min_s=5, max_s=7)
        self._scatter_obstacles(level, cemetery, density=0.05)   # tombstones
        self._scatter_obstacles(level, field, density=0.07)      # trees / hedges

        # One dungeon entrance per themed quadrant, on a cleared open tile.
        cx, cy = self._place_clearing(level, cemetery)
        level.tiles[cx][cy].type = TileType.STAIRS_DOWN
        level.stairs_down_crypt = (cx, cy)
        fx, fy = self._place_clearing(level, farm)
        level.tiles[fx][fy].type = TileType.STAIRS_DOWN
        level.stairs_down_cellar = (fx, fy)
        vx, vy = self._place_clearing(level, field)
        level.tiles[vx][vy].type = TileType.STAIRS_DOWN
        level.stairs_down_cave = (vx, vy)

        # Player begins in the town quadrant.
        level.player_spawn = self._place_clearing(level, town)

        # Friendly NPCs scattered through their biomes.
        self._scatter_npcs(level, town, farm, cemetery, field)

        # Fog of war: this large world is revealed as the player explores it.
        return level

    # ------------------------------------------------------------------
    # Overworld procedural helpers
    # ------------------------------------------------------------------
    def _scatter_houses(self, level, region, count, min_s, max_s):
        rng = self._rng
        x0, y0, x1, y1 = region
        placed = []
        attempts = count * 8
        while count > 0 and attempts > 0:
            attempts -= 1
            w = rng.randint(min_s, max_s)
            h = rng.randint(min_s, max_s)
            if x0 + w >= x1 or y0 + h >= y1:
                continue
            hx = rng.randint(x0, x1 - w)
            hy = rng.randint(y0, y1 - h)
            pad = (hx - 1, hy - 1, hx + w + 1, hy + h + 1)
            if any(self._rects_overlap(pad, p) for p in placed):
                continue
            door = (hx + w // 2, hy + h - 1)  # door on the bottom wall
            self._build_house(level, hx, hy, w, h, TileType.WALL, door_pos=door)
            placed.append((hx, hy, hx + w, hy + h))
            count -= 1

    @staticmethod
    def _rects_overlap(a, b) -> bool:
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]

    def _scatter_obstacles(self, level, region, density):
        rng = self._rng
        x0, y0, x1, y1 = region
        for x in range(x0, x1):
            for y in range(y0, y1):
                if level.tiles[x][y].type == TileType.FLOOR and rng.random() < density:
                    level.tiles[x][y].type = TileType.WALL

    def _scatter_fences(self, level, region, count):
        rng = self._rng
        x0, y0, x1, y1 = region
        for _ in range(count):
            if rng.random() < 0.5:
                # horizontal fence with a gate gap
                fy = rng.randint(y0 + 1, y1 - 2)
                gx = rng.randint(x0, x1)
                for x in range(x0, x1):
                    if abs(x - gx) > 1 and level.tiles[x][fy].type == TileType.FLOOR:
                        level.tiles[x][fy].type = TileType.WALL
            else:
                fx = rng.randint(x0 + 1, x1 - 2)
                gy = rng.randint(y0, y1)
                for y in range(y0, y1):
                    if abs(y - gy) > 1 and level.tiles[fx][y].type == TileType.FLOOR:
                        level.tiles[fx][y].type = TileType.WALL

    def _place_clearing(self, level, region) -> tuple[int, int]:
        """Pick an open floor tile in the region and clear a small area around
        it so it is reachable; returns the tile."""
        rng = self._rng
        x0, y0, x1, y1 = region
        spot = ((x0 + x1) // 2, (y0 + y1) // 2)
        for _ in range(500):
            x = rng.randint(x0 + 1, x1 - 2)
            y = rng.randint(y0 + 1, y1 - 2)
            if level.tiles[x][y].type == TileType.FLOOR:
                spot = (x, y)
                break
        sx, sy = spot
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = sx + dx, sy + dy
                if 0 < nx < level.width - 1 and 0 < ny < level.height - 1:
                    level.tiles[nx][ny].type = TileType.FLOOR
        return spot

    def _scatter_npcs(self, level, town, farm, cemetery, field):
        from Entities.npc import NPC
        from UI.colors import Color
        rng = self._rng

        specs = [
            (town, "villager", Color.CYAN, _VILLAGER_LINES, ["Town Crier", "Townsfolk", "Innkeeper"]),
            (farm, "farmer", Color.YELLOW, _FARMER_LINES, ["Farmer Giles", "Farm Boy", "Shepherd"]),
            (cemetery, "ghost_npc", Color.WHITE, _GHOST_LINES, ["Friendly Spirit", "Ancestor Ghost", "Pale Wisp"]),
            (field, "druid", Color.GREEN, _DRUID_LINES, ["Druid Oakwood", "Field Fairy", "Wanderer"]),
        ]
        spawn = level.player_spawn
        for region, ntype, color, lines, names in specs:
            x0, y0, x1, y1 = region
            for name in names:
                placed = False
                for _ in range(80):
                    x = rng.randint(x0 + 1, x1 - 2)
                    y = rng.randint(y0 + 1, y1 - 2)
                    if (level.tiles[x][y].type == TileType.FLOOR
                            and (x, y) != spawn
                            and level.monster_at(x, y) is None):
                        level.monsters.append(NPC(name, ntype, ntype[0].upper(), color, list(lines), x=x, y=y))
                        placed = True
                        break

    def _build_house(self, level: DungeonLevel, hx: int, hy: int, hw: int, hh: int, wall_type: TileType, door_pos: tuple[int, int]):
        for x in range(hx, hx + hw):
            for y in range(hy, hy + hh):
                if x == hx or x == hx + hw - 1 or y == hy or y == hy + hh - 1:
                    level.tiles[x][y].type = wall_type
                else:
                    level.tiles[x][y].type = TileType.FLOOR
        dx, dy = door_pos
        level.tiles[dx][dy].type = TileType.FLOOR
