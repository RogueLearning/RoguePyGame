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

        if depth >= 1:
            stairs_up = rooms[0].center
            level.tiles[stairs_up[0]][stairs_up[1]].type = TileType.STAIRS_UP
            level.stairs_up = stairs_up
            level.has_stairs_up = True

        should_spawn_boss = allow_boss_spawn and depth > 3 and self._rng.randrange(100) < 15
        if should_spawn_boss and len(rooms) > 1:
            room_index = self._rng.randrange(1, len(rooms))
            bx, by = rooms[room_index].random_point(self._rng)
            level.monsters.append(monster_factory.create_boss(bx, by))

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

    def generate_overworld(self) -> DungeonLevel:
        level = DungeonLevel(30, 18)
        level.is_overworld = True
        
        # 1. Fill the level with FLOOR first
        for x in range(30):
            for y in range(18):
                level.tiles[x][y].type = TileType.FLOOR
                
        # 2. Carve buildings and fences for the Town (Top-Left)
        # Town house 1: Cozy cottage
        self._build_house(level, 2, 2, 6, 5, wall_type=TileType.WALL, door_pos=(4, 6))
        # Town house 2: Shop / Tavern structure
        self._build_house(level, 9, 2, 5, 5, wall_type=TileType.WALL, door_pos=(11, 6))
        
        # 3. Carve farmhouse and fences for the Farm (Top-Right)
        # Farmhouse
        self._build_house(level, 18, 2, 6, 5, wall_type=TileType.WALL, door_pos=(20, 6))
        # Farm fence dividing line
        for x in range(15, 29):
            level.tiles[x][7].type = TileType.WALL
        # Opening/gate in the fence
        level.tiles[22][7].type = TileType.FLOOR
        
        # 4. Carve Mausoleum in the Cemetery (Bottom-Left)
        self._build_house(level, 3, 11, 5, 5, wall_type=TileType.WALL, door_pos=(5, 15))
        
        # Scattered tombstones
        tombstones = [(2, 10), (8, 10), (10, 12), (8, 14), (12, 15)]
        for tx, ty in tombstones:
            level.tiles[tx][ty].type = TileType.WALL
            
        # 5. Carve trees/hedges in the Field (Bottom-Right)
        trees = [(17, 11), (22, 10), (27, 12), (19, 14), (25, 15), (28, 16)]
        for tx, ty in trees:
            level.tiles[tx][ty].type = TileType.WALL
            
        # 6. Place Dungeon Entrance staircases (TileType.STAIRS_DOWN)
        # Crypt Stairs inside the Mausoleum
        level.tiles[5][13].type = TileType.STAIRS_DOWN
        level.stairs_down_crypt = (5, 13)
        
        # Cellar Hatch inside the Farmhouse
        level.tiles[20][4].type = TileType.STAIRS_DOWN
        level.stairs_down_cellar = (20, 4)
        
        # Cave Portal in the Field
        level.tiles[24][13].type = TileType.STAIRS_DOWN
        level.stairs_down_cave = (24, 13)
        
        # 7. Spawn friendly overworld NPCs
        from Entities.npc import NPC
        from UI.colors import Color
        
        # Town NPCs
        level.monsters.append(NPC("Town Crier", "villager", "V", Color.BLUE, [
            "Hear ye, hear ye! Multiple dungeons have opened around the overworld!",
            "Welcome to our town! Beware the crypt in the cemetery, it is highly dangerous.",
            "Make sure to equip your gear by pressing [I] before going underground!"
        ], x=6, y=7))
        
        level.monsters.append(NPC("Townsman", "villager", "V", Color.CYAN, [
            "Nice day for an adventure, isn't it?",
            "If you get hurt, look for a glowing water fountain to restore your health.",
            "I heard the Knight class blocks 1 damage from every single monster hit!"
        ], x=11, y=7))
        
        # Farm NPCs
        level.monsters.append(NPC("Farmer Giles", "farmer", "F", Color.YELLOW, [
            "Watch out for my crops! The tilled soil takes hard work to maintain.",
            "The old cellar in my house is infested with giant rats and worse...",
            "A Rogue is very agile and has a 30% chance to hit for a double-damage critical strike!"
        ], x=21, y=6))
        
        level.monsters.append(NPC("Farm Boy", "farmer", "F", Color.DARK_YELLOW, [
            "I saw some gold coins drop near the cellar entrance. You should check it out.",
            "Beware of chests that look slightly off... some are actually Mimics!",
            "If you need weapons or magic wands, there is a mysterious merchant down in the depths."
        ], x=25, y=3))
        
        # Cemetery NPCs (Ghosts)
        level.monsters.append(NPC("Friendly Spirit", "ghost_npc", "G", Color.WHITE, [
            "Booo... don't run away! I am just a friendly spirit watching over the graves.",
            "The crypt entrance inside the mausoleum leads deep into the undead catacombs.",
            "Wizards are highly attuned to magic and recharge their wand charges over time!"
        ], x=3, y=14))
        
        level.monsters.append(NPC("Ancestor Ghost", "ghost_npc", "G", Color.GRAY, [
            "Rest in peace... but watch your step, the crypt contains dreadful creatures.",
            "If a chest is locked, search the floor thoroughly. The key is always nearby.",
            "Only enchanted steel can harm the boss monsters. Bless your weapons at fountains!"
        ], x=11, y=14))
        
        # Field NPCs (Druids)
        level.monsters.append(NPC("Druid Oakwood", "druid", "D", Color.GREEN, [
            "Nature is peaceful, but the mysterious cave to the east is full of darkness.",
            "Equip your bow and arrows to shoot monsters from a safe distance!",
            "May the stars guide you through the dark dungeons below."
        ], x=18, y=12))
        
        level.monsters.append(NPC("Field Fairy", "druid", "D", Color.MAGENTA, [
            "Tee-hee! Have you visited all three dungeons yet?",
            "Use the arrow keys or WASD to move and face monsters to attack them.",
            "Press [Enter] when standing on a portal to enter or exit a dungeon!"
        ], x=26, y=14))
        
        # 8. Setup spawn & explore defaults
        level.player_spawn = (5, 8)
        for x in range(30):
            for y in range(18):
                level.tiles[x][y].explored = True
                
        return level

    def _build_house(self, level: DungeonLevel, hx: int, hy: int, hw: int, hh: int, wall_type: TileType, door_pos: tuple[int, int]):
        for x in range(hx, hx + hw):
            for y in range(hy, hy + hh):
                if x == hx or x == hx + hw - 1 or y == hy or y == hy + hh - 1:
                    level.tiles[x][y].type = wall_type
                else:
                    level.tiles[x][y].type = TileType.FLOOR
        dx, dy = door_pos
        level.tiles[dx][dy].type = TileType.FLOOR
