import sys
import math
import random
import pygame

from Entities.player import Player
from Map.dungeon_level import DungeonLevel
from Map.tile import TileType
from UI.colors import Color, color_rgb
from UI.message_log import MessageLog

# Screen and Layout Constants
TILE_SIZE = 32
MAP_WIDTH = 30
MAP_HEIGHT = 18
MAP_PIXEL_WIDTH = MAP_WIDTH * TILE_SIZE
MAP_PIXEL_HEIGHT = MAP_HEIGHT * TILE_SIZE

SIDEBAR_WIDTH = 320
LOG_HEIGHT = 144

TOTAL_WIDTH = MAP_PIXEL_WIDTH + SIDEBAR_WIDTH
TOTAL_HEIGHT = MAP_PIXEL_HEIGHT + LOG_HEIGHT


class Renderer:
    def __init__(self):
        # Initialize pygame display
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        self._screen = pygame.display.set_mode((TOTAL_WIDTH, TOTAL_HEIGHT))
        pygame.display.set_caption("Rogue PyGame - Wizard's Quest")

        # Fonts
        self._init_fonts()

        # Animation states
        self._entity_positions = {}  # entity -> [current_x, current_y]
        self._bumps = {}            # entity -> {"dx": dx, "dy": dy, "progress": 0.0, "speed": 0.15}
        self._projectiles = []       # list of dicts: {"type": "fireball", "path": [...], "index": 0.0, "speed": 0.3, "callback": func}
        self._damage_texts = []      # list of dicts: {"text": str, "x": float, "y": float, "color": tuple, "life": float}
        self._particles = []         # list of dicts: {"x": float, "y": float, "vx": float, "vy": float, "color": tuple, "size": float, "life": float, "max_life": float}
        
        self._shake_intensity = 0.0
        self._shake_decay = 0.85
        self._frame_count = 0

        # Load animated spritesheet
        self._spritesheet = None
        try:
            self._spritesheet = pygame.image.load("assets/knight_spritesheet.png").convert_alpha()
        except Exception:
            pass


    def _init_fonts(self):
        # Try to find a premium looking font, fallback to standard system fonts
        self._ui_font = None
        font_name = None
        for name in ["outfit", "inter", "segoe ui", "helvetica", "arial", "courier"]:
            try:
                self._ui_font = pygame.font.SysFont(name, 18)
                if self._ui_font:
                    font_name = name
                    break
            except Exception:
                pass
        if not self._ui_font:
            self._ui_font = pygame.font.SysFont(None, 18)

        # Bold headers
        self._header_font = pygame.font.SysFont(font_name, 22, bold=True)
        # Title font
        self._title_font = pygame.font.SysFont(font_name, 48, bold=True)
        # Log font - monospaced is nice, fallback to UI font
        self._log_font = None
        try:
            self._log_font = pygame.font.SysFont("courier", 16)
        except Exception:
            self._log_font = self._ui_font


    def reset(self):
        # For backward compatibility with terminal redrawing triggers
        pass

    def trigger_shake(self, intensity=6.0):
        self._shake_intensity = intensity

    def add_damage_text(self, tile_x: int, tile_y: int, text: str, color: tuple[int, int, int]):
        self._damage_texts.append({
            "text": text,
            "x": (tile_x + 0.5) * TILE_SIZE,
            "y": tile_y * TILE_SIZE,
            "color": color,
            "life": 1.0,
            "max_life": 1.0
        })

    def add_particles(self, tile_x: int, tile_y: int, color: tuple[int, int, int], count=10):
        px = (tile_x + 0.5) * TILE_SIZE
        py = (tile_y + 0.5) * TILE_SIZE
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2.5)
            self._particles.append({
                "x": px,
                "y": py,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "color": color,
                "size": random.uniform(2, 4),
                "life": random.uniform(0.3, 0.7),
                "max_life": 1.0
            })

    def add_projectile(self, path: list[tuple[int, int]], callback, type="lightning"):
        self._projectiles.append({
            "path": path,
            "index": 0.0,
            "speed": 0.45 if type == "lightning" else 0.35,  # Lightning travels faster!
            "callback": callback,
            "type": type
        })

    def add_bump(self, entity, target_tile: tuple[int, int]):
        dx = target_tile[0] - entity.x
        dy = target_tile[1] - entity.y
        self._bumps[entity] = {
            "dx": dx,
            "dy": dy,
            "progress": 0.0,
            "speed": 0.2
        }

    def is_animating(self) -> bool:
        return len(self._projectiles) > 0

    def update_animations(self):
        self._frame_count += 1

        # 1. Update Shake
        self._shake_intensity *= self._shake_decay
        if self._shake_intensity < 0.1:
            self._shake_intensity = 0.0

        # 2. Update Damage Texts
        for dt in list(self._damage_texts):
            dt["life"] -= 0.02
            dt["y"] -= 0.5  # Float up
            if dt["life"] <= 0:
                self._damage_texts.remove(dt)

        # 3. Update Particles
        for p in list(self._particles):
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 0.02
            if p["life"] <= 0:
                self._particles.remove(p)

        # 4. Update Bumps
        for entity in list(self._bumps.keys()):
            bump = self._bumps[entity]
            bump["progress"] += bump["speed"]
            if bump["progress"] >= 1.0:
                del self._bumps[entity]

        # 5. Update Projectiles
        for proj in list(self._projectiles):
            path = proj["path"]
            proj["index"] += proj["speed"]
            
            # Spawn trail particles at the current projectile position
            idx = int(proj["index"])
            ptype = proj.get("type", "lightning")
            if idx < len(path) - 1:
                frac = proj["index"] - idx
                t1 = path[idx]
                t2 = path[idx + 1]
                px = (t1[0] + (t2[0] - t1[0]) * frac + 0.5) * TILE_SIZE
                py = (t1[1] + (t2[1] - t1[1]) * frac + 0.5) * TILE_SIZE
                if ptype == "lightning":
                    self._particles.append({
                        "x": px,
                        "y": py,
                        "vx": random.uniform(-0.6, 0.6),
                        "vy": random.uniform(-0.6, 0.6),
                        "color": (100, 200, 255) if random.random() > 0.4 else (255, 255, 255),
                        "size": random.uniform(2, 4),
                        "life": random.uniform(0.15, 0.35),
                        "max_life": 1.0
                    })
                else:
                    self._particles.append({
                        "x": px,
                        "y": py,
                        "vx": random.uniform(-0.4, 0.4),
                        "vy": random.uniform(-0.4, 0.4),
                        "color": (250, 120, 20) if random.random() > 0.3 else (250, 220, 40),
                        "size": random.uniform(3, 6),
                        "life": random.uniform(0.2, 0.4),
                        "max_life": 1.0
                    })

            if proj["index"] >= len(path) - 1:
                # Finished!
                self._projectiles.remove(proj)
                dest = path[-1]
                if ptype == "lightning":
                    self.add_particles(dest[0], dest[1], (100, 200, 255), count=15)
                    self.add_particles(dest[0], dest[1], (255, 255, 255), count=8)
                else:
                    self.add_particles(dest[0], dest[1], (230, 55, 55), count=18)
                    self.add_particles(dest[0], dest[1], (235, 195, 45), count=12)
                self.trigger_shake(8.0)
                proj["callback"]()

    def render(self, level: DungeonLevel, player: Player, log: MessageLog, show_inventory=False, show_shop=None):
        # Tick calculations
        self.update_animations()

        # Background clearing
        self._screen.fill((12, 12, 16))

        # Calculate screen shake offset
        shake_x = 0
        shake_y = 0
        if self._shake_intensity > 0.0:
            shake_x = int(random.uniform(-self._shake_intensity, self._shake_intensity))
            shake_y = int(random.uniform(-self._shake_intensity, self._shake_intensity))

        # Render Map Grid
        self._draw_map(level, shake_x, shake_y)

        # Render Items
        self._draw_items(level, shake_x, shake_y)

        # Render Entities
        self._draw_entities(level, player, shake_x, shake_y)

        # Render Fireball Projectiles (Visuals)
        self._draw_projectiles(shake_x, shake_y)

        # Render Particles
        self._draw_particles(shake_x, shake_y)

        # Render Damage text overlay
        self._draw_damage_texts(shake_x, shake_y)

        # Render Sidebar (No shake)
        self._draw_sidebar(player)

        # Render Message Log (No shake)
        self._draw_log(log)

        # Draw inventory modal if requested
        if show_inventory:
            self._draw_inventory_overlay(player)

        # Draw shop modal if requested
        if show_shop:
            self._draw_shop_overlay(player, show_shop)

        pygame.display.flip()

    def _draw_map(self, level: DungeonLevel, shake_x: int, shake_y: int):
        w = min(MAP_WIDTH, level.width)
        h = min(MAP_HEIGHT, level.height)
        
        for x in range(w):
            for y in range(h):
                t = level.tiles[x][y]
                if not t.explored:
                    continue

                rect = pygame.Rect(x * TILE_SIZE + shake_x, y * TILE_SIZE + shake_y, TILE_SIZE, TILE_SIZE)

                # Fetch basic tile color definitions
                visible = t.visible

                if t.type == TileType.WALL:
                    color = color_rgb(Color.DARK_CYAN) if visible else color_rgb(Color.DARK_BLUE)
                    self._draw_brick_wall(rect, color)
                elif t.type == TileType.FLOOR:
                    color = (36, 32, 28) if visible else (20, 20, 24)
                    self._draw_floor(rect, color, visible)
                elif t.type == TileType.STAIRS_DOWN:
                    color = (25, 23, 20) if visible else (16, 16, 20)
                    self._draw_floor(rect, color, visible)
                    stairs_color = color_rgb(Color.YELLOW) if visible else color_rgb(Color.DARK_YELLOW)
                    self._draw_stairs_down(rect, stairs_color)
                elif t.type == TileType.STAIRS_UP:
                    color = (25, 23, 20) if visible else (16, 16, 20)
                    self._draw_floor(rect, color, visible)
                    stairs_color = color_rgb(Color.WHITE) if visible else color_rgb(Color.GRAY)
                    self._draw_stairs_up(rect, stairs_color)
                elif t.type == TileType.FOUNTAIN:
                    color = (25, 23, 20) if visible else (16, 16, 20)
                    self._draw_floor(rect, color, visible)
                    self._draw_fountain(rect, visible)

                    # Emit bubbling water drops if visible
                    if visible and self._frame_count % 10 == 0:
                        self._particles.append({
                            "x": rect.centerx + random.uniform(-6, 6),
                            "y": rect.bottom - 16,
                            "vx": random.uniform(-0.3, 0.3),
                            "vy": random.uniform(-0.8, -0.2),
                            "color": (100, 190, 255) if random.random() > 0.4 else (255, 255, 255),
                            "size": random.uniform(1.5, 3),
                            "life": random.uniform(0.4, 0.8),
                            "max_life": 1.0
                        })

    def _draw_brick_wall(self, rect: pygame.Rect, color: tuple[int, int, int]):
        pygame.draw.rect(self._screen, color, rect)
        
        # Highlight and shadow borders for 3D bevel look
        hl = tuple(min(255, c + 35) for c in color)
        sd = tuple(max(0, c - 30) for c in color)
        pygame.draw.line(self._screen, hl, rect.topleft, rect.topright)
        pygame.draw.line(self._screen, hl, rect.topleft, rect.bottomleft)
        pygame.draw.line(self._screen, sd, rect.bottomleft, rect.bottomright)
        pygame.draw.line(self._screen, sd, rect.topright, rect.bottomright)

        # Mortar bricks
        mortar = tuple(max(0, c - 20) for c in color)
        pygame.draw.line(self._screen, mortar, (rect.left, rect.top + 16), (rect.right, rect.top + 16))
        pygame.draw.line(self._screen, mortar, (rect.left + 16, rect.top), (rect.left + 16, rect.top + 16))
        pygame.draw.line(self._screen, mortar, (rect.left + 8, rect.top + 16), (rect.left + 8, rect.bottom))

    def _draw_floor(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        pygame.draw.rect(self._screen, color, rect)
        
        # Draw neat dot patterns representing floor gravel
        dot_color = (80, 70, 60) if visible else (45, 45, 50)
        pygame.draw.circle(self._screen, dot_color, (rect.centerx - 6, rect.centery), 1)
        pygame.draw.circle(self._screen, dot_color, (rect.centerx + 6, rect.centery), 1)

    def _draw_stairs_down(self, rect: pygame.Rect, color: tuple[int, int, int]):
        # Series of step bars leading down
        for i in range(3):
            y = rect.top + 9 + i * 5
            x_left = rect.left + 6 + i * 4
            x_right = rect.right - 6 - i * 4
            pygame.draw.line(self._screen, color, (x_left, y), (x_right, y), 3)

    def _draw_stairs_up(self, rect: pygame.Rect, color: tuple[int, int, int]):
        # Series of step bars leading up
        for i in range(3):
            y = rect.bottom - 9 - i * 5
            x_left = rect.left + 6 + i * 4
            x_right = rect.right - 6 - i * 4
            pygame.draw.line(self._screen, color, (x_left, y), (x_right, y), 3)

    def _draw_fountain(self, rect: pygame.Rect, visible: bool):
        pedestal_c = (90, 90, 95) if visible else (50, 50, 55)
        basin_c = (110, 110, 115) if visible else (65, 65, 70)
        water_c = (40, 140, 220) if visible else (25, 60, 95)

        # Fountain Pedestal Base
        base_rect = pygame.Rect(rect.left + 6, rect.bottom - 10, 20, 7)
        pygame.draw.rect(self._screen, pedestal_c, base_rect, border_radius=1)

        # Basin cup
        basin_rect = pygame.Rect(rect.left + 3, rect.bottom - 18, 26, 9)
        pygame.draw.rect(self._screen, basin_c, basin_rect, border_radius=3)

        # Water surface inside basin
        water_rect = pygame.Rect(rect.left + 5, rect.bottom - 16, 22, 4)
        pygame.draw.rect(self._screen, water_c, water_rect)

    def _draw_items(self, level: DungeonLevel, shake_x: int, shake_y: int):
        for ie in level.items:
            if ie.x >= MAP_WIDTH or ie.y >= MAP_HEIGHT:
                continue
            if not level.tiles[ie.x][ie.y].visible:
                continue

            rect = pygame.Rect(ie.x * TILE_SIZE + shake_x, ie.y * TILE_SIZE + shake_y, TILE_SIZE, TILE_SIZE)
            color = color_rgb(ie.item.color)

            if ie.item.kind.value == "healing_potion":
                self._draw_potion(rect, color)
            elif ie.item.kind.value == "weapon":
                self._draw_weapon(rect, color)
            elif ie.item.kind.value == "wand":
                self._draw_wand(rect, color)
            elif ie.item.kind.value == "coin":
                self._draw_coin(rect)
            elif ie.item.kind.value == "key":
                self._draw_key(rect)
            else:
                # Fallback circular pouch item
                pygame.draw.circle(self._screen, color, rect.center, 6)

    def _draw_key(self, rect: pygame.Rect):
        # Golden Key drawing
        # Head ring
        pygame.draw.circle(self._screen, (235, 180, 25), (rect.centerx - 4, rect.centery), 4, 1)
        # Shaft
        pygame.draw.line(self._screen, (235, 180, 25), (rect.centerx, rect.centery), (rect.centerx + 8, rect.centery), 2)
        # Teeth
        pygame.draw.line(self._screen, (235, 180, 25), (rect.centerx + 5, rect.centery), (rect.centerx + 5, rect.centery + 3), 2)
        pygame.draw.line(self._screen, (235, 180, 25), (rect.centerx + 7, rect.centery), (rect.centerx + 7, rect.centery + 3), 2)

    def _draw_coin(self, rect: pygame.Rect):
        # Shiny Gold Coin drawing
        # Outer ring
        pygame.draw.circle(self._screen, (240, 195, 30), rect.center, 7)
        # Inner detail circle
        pygame.draw.circle(self._screen, (255, 230, 80), (rect.centerx - 1, rect.centery - 1), 4)
        # Darker border
        pygame.draw.circle(self._screen, (185, 140, 10), rect.center, 7, 1)

    def _draw_potion(self, rect: pygame.Rect, color: tuple[int, int, int]):
        # Flask neck
        pygame.draw.rect(self._screen, (180, 180, 185), (rect.centerx - 2, rect.top + 6, 4, 7))
        # Flask cork
        pygame.draw.rect(self._screen, (120, 80, 40), (rect.centerx - 2, rect.top + 3, 4, 3))
        # Flask circular body
        pygame.draw.circle(self._screen, (190, 190, 195), (rect.centerx, rect.bottom - 10), 8, 2)
        # Red liquid fill
        pygame.draw.circle(self._screen, color, (rect.centerx, rect.bottom - 10), 6)
        # Shine spot
        pygame.draw.circle(self._screen, (255, 255, 255), (rect.centerx - 2, rect.bottom - 12), 2)

    def _draw_weapon(self, rect: pygame.Rect, color: tuple[int, int, int]):
        # Diagonal sword vector lines
        start = (rect.left + 6, rect.bottom - 6)
        end = (rect.right - 6, rect.top + 6)
        
        # Blade steel
        pygame.draw.line(self._screen, (210, 210, 215), start, end, 3)

        # Crossguard and handle
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        if length > 0:
            mid_x = start[0] + dx * 0.25
            mid_y = start[1] + dy * 0.25
            px = -dy / length
            py = dx / length
            
            # Draw crossguard perpendicular to blade
            guard_start = (mid_x - px * 5, mid_y - py * 5)
            guard_end = (mid_x + px * 5, mid_y + py * 5)
            pygame.draw.line(self._screen, color, guard_start, guard_end, 2)

            # Draw brown wood hilt
            hilt_end = (start[0] + dx * 0.08, start[1] + dy * 0.08)
            pygame.draw.line(self._screen, (110, 75, 40), start, hilt_end, 3)

    def _draw_wand(self, rect: pygame.Rect, color: tuple[int, int, int]):
        start = (rect.left + 7, rect.bottom - 7)
        end = (rect.right - 7, rect.top + 7)
        # Wooden shaft
        pygame.draw.line(self._screen, (100, 70, 40), start, end, 3)
        # Spark tip
        pygame.draw.circle(self._screen, color, end, 4)
        pygame.draw.circle(self._screen, (255, 255, 255), end, 2)

    def _draw_entities(self, level: DungeonLevel, player: Player, shake_x: int, shake_y: int):
        # Render Monsters
        for m in level.monsters:
            if not m.is_alive:
                continue
            if m.x >= MAP_WIDTH or m.y >= MAP_HEIGHT:
                continue
            if not level.tiles[m.x][m.y].visible:
                continue

            # Visual position interpolation
            vx, vy = self._get_interpolated_pos(m)
            
            # Add bump offsets if attacking
            ox, oy = self._get_bump_offset(m)
            
            rect = pygame.Rect(vx + ox + shake_x, vy + oy + shake_y, TILE_SIZE, TILE_SIZE)
            self._draw_monster_sprite(rect, m.name, color_rgb(m.color))

        # Render Player
        if player.x < MAP_WIDTH and player.y < MAP_HEIGHT:
            vx, vy = self._get_interpolated_pos(player)
            ox, oy = self._get_bump_offset(player)
            rect = pygame.Rect(vx + ox + shake_x, vy + oy + shake_y, TILE_SIZE, TILE_SIZE)
            
            enchanted = (player.inventory.equipped_weapon and player.inventory.equipped_weapon.is_enchanted)
            self._draw_player_sprite(rect, color_rgb(player.color), enchanted, player=player)

    def _get_interpolated_pos(self, entity) -> tuple[float, float]:
        target_x = entity.x * TILE_SIZE
        target_y = entity.y * TILE_SIZE
        
        if entity not in self._entity_positions:
            self._entity_positions[entity] = [target_x, target_y]
            return target_x, target_y
            
        cur = self._entity_positions[entity]
        # Smooth interpolation
        cur[0] += (target_x - cur[0]) * 0.28
        cur[1] += (target_y - cur[1]) * 0.28
        
        # Snap if extremely close
        if math.hypot(target_x - cur[0], target_y - cur[1]) < 0.5:
            cur[0], cur[1] = target_x, target_y

        return cur[0], cur[1]

    def _get_bump_offset(self, entity) -> tuple[float, float]:
        if entity not in self._bumps:
            return 0.0, 0.0
            
        bump = self._bumps[entity]
        # Sine wave bump animation (starts at 0, peaks at 0.5, returns to 0)
        factor = math.sin(bump["progress"] * math.pi)
        ox = bump["dx"] * TILE_SIZE * 0.5 * factor
        oy = bump["dy"] * TILE_SIZE * 0.5 * factor
        return ox, oy

    def _draw_monster_sprite(self, rect: pygame.Rect, name: str, color: tuple[int, int, int]):
        if name == "rat":
            # Rat body ellipse
            body_rect = pygame.Rect(rect.centerx - 7, rect.centery - 3, 14, 7)
            pygame.draw.ellipse(self._screen, color, body_rect)
            # Head circle
            pygame.draw.circle(self._screen, color, (rect.centerx + 6, rect.centery - 1), 3.5)
            # Pink tail line
            pygame.draw.line(self._screen, (220, 160, 160), (rect.centerx - 7, rect.centery), (rect.centerx - 13, rect.centery + 3))
        elif name == "goblin":
            # Head
            pygame.draw.circle(self._screen, color, rect.center, 8)
            # Ears
            pygame.draw.polygon(self._screen, color, [(rect.centerx - 8, rect.centery), (rect.centerx - 12, rect.centery - 5), (rect.centerx - 5, rect.centery - 3)])
            pygame.draw.polygon(self._screen, color, [(rect.centerx + 8, rect.centery), (rect.centerx + 12, rect.centery - 5), (rect.centerx + 5, rect.centery - 3)])
            # Red eyes
            pygame.draw.circle(self._screen, (230, 40, 40), (rect.centerx - 3, rect.centery - 1.5), 1)
            pygame.draw.circle(self._screen, (230, 40, 40), (rect.centerx + 3, rect.centery - 1.5), 1)
        elif name == "orc":
            # Head
            pygame.draw.circle(self._screen, color, rect.center, 10)
            # Tusks (White pixels)
            pygame.draw.polygon(self._screen, (245, 245, 245), [(rect.centerx - 5, rect.centery + 3), (rect.centerx - 7, rect.centery - 1), (rect.centerx - 3, rect.centery + 1)])
            pygame.draw.polygon(self._screen, (245, 245, 245), [(rect.centerx + 5, rect.centery + 3), (rect.centerx + 7, rect.centery - 1), (rect.centerx + 3, rect.centery + 1)])
            # Yellow eyes
            pygame.draw.circle(self._screen, (250, 230, 20), (rect.centerx - 3.5, rect.centery - 1.5), 1.5)
            pygame.draw.circle(self._screen, (250, 230, 20), (rect.centerx + 3.5, rect.centery - 1.5), 1.5)
        elif name == "troll":
            # Large rectangular troll block
            troll_rect = pygame.Rect(rect.centerx - 11, rect.centery - 11, 22, 22)
            pygame.draw.rect(self._screen, color, troll_rect, border_radius=4)
            # Yellow eyes
            pygame.draw.circle(self._screen, (255, 255, 255), (rect.centerx - 4, rect.centery - 4), 2)
            pygame.draw.circle(self._screen, (255, 255, 255), (rect.centerx + 4, rect.centery - 4), 2)
            # Wooden club
            pygame.draw.line(self._screen, (120, 80, 40), (rect.centerx + 7, rect.centery + 5), (rect.centerx + 13, rect.centery - 5), 4)
        elif name == "wraith":
            # Translucent ghost polygon representation
            ghost_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(ghost_surface, color + (160,), (16, 12), 8)
            pygame.draw.polygon(ghost_surface, color + (160,), [(8, 12), (24, 12), (16, 28)])
            # Eyes (glow white)
            pygame.draw.circle(ghost_surface, (255, 255, 255, 250), (13, 11), 2)
            pygame.draw.circle(ghost_surface, (255, 255, 255, 250), (19, 11), 2)
            self._screen.blit(ghost_surface, rect.topleft)
        elif name == "dread knight":
            # Armored skull
            pygame.draw.circle(self._screen, (35, 35, 40), rect.center, 11)
            # Helmet visor and burning red eyes
            pygame.draw.rect(self._screen, (240, 30, 30), (rect.centerx - 7, rect.centery - 3, 14, 3))
            # Horn spikes
            pygame.draw.polygon(self._screen, (75, 75, 80), [(rect.centerx - 7, rect.top + 7), (rect.centerx - 11, rect.top + 2), (rect.centerx - 4, rect.top + 8)])
            pygame.draw.polygon(self._screen, (75, 75, 80), [(rect.centerx + 7, rect.top + 7), (rect.centerx + 11, rect.top + 2), (rect.centerx + 4, rect.top + 8)])
        elif name == "merchant":
            # Cozy brown hooded figure with a gold collar/emblem
            # Cloak body
            cloak_rect = pygame.Rect(rect.left + 4, rect.centery - 2, 24, 16)
            pygame.draw.ellipse(self._screen, (100, 65, 35), cloak_rect)
            
            # Hood
            pygame.draw.circle(self._screen, (120, 80, 50), (rect.centerx, rect.centery - 4), 9)
            
            # Face opening
            pygame.draw.circle(self._screen, (25, 20, 15), (rect.centerx, rect.centery - 4), 6)
            
            # Glowing gold eyes
            pygame.draw.circle(self._screen, (255, 215, 0), (rect.centerx - 2, rect.centery - 5), 1)
            pygame.draw.circle(self._screen, (255, 215, 0), (rect.centerx + 2, rect.centery - 5), 1)
            
            # Gold emblem/collar
            emblem_rect = pygame.Rect(rect.centerx - 3, rect.centery + 3, 6, 6)
            pygame.draw.ellipse(self._screen, (255, 215, 0), emblem_rect)
        elif name in ("chest", "locked chest"):
            # Draw chest box (wooden container)
            box_rect = pygame.Rect(rect.left + 5, rect.centery - 4, 22, 16)
            # Brown body
            pygame.draw.rect(self._screen, (139, 69, 19), box_rect, border_radius=2)
            # Gold banding on left and right edges
            pygame.draw.rect(self._screen, (220, 180, 40), (rect.left + 5, rect.centery - 4, 3, 16))
            pygame.draw.rect(self._screen, (220, 180, 40), (rect.right - 8, rect.centery - 4, 3, 16))
            # Top lid line
            pygame.draw.line(self._screen, (90, 45, 10), (rect.left + 5, rect.centery - 4), (rect.right - 6, rect.centery - 4), 2)
            
            # Draw Lock/Keyhole
            lock_color = (255, 215, 0) if name == "locked chest" else (180, 180, 185)
            # Lock plate
            pygame.draw.rect(self._screen, lock_color, (rect.centerx - 3, rect.centery + 1, 6, 6), border_radius=1)
            # Tiny keyhole dot
            pygame.draw.circle(self._screen, (30, 30, 30), (rect.centerx, rect.centery + 4), 1)
        elif name == "mimic":
            # Gaping chest with teeth and tongue
            # Base (brown wood)
            pygame.draw.rect(self._screen, (139, 69, 19), (rect.left + 5, rect.centery + 2, 22, 10), border_radius=1)
            # Gaping mouth (red surface inside)
            pygame.draw.rect(self._screen, (200, 30, 30), (rect.left + 5, rect.centery - 6, 22, 9))
            # Upper lid askew
            pygame.draw.rect(self._screen, (110, 50, 15), (rect.left + 4, rect.centery - 12, 24, 7), border_radius=1)
            
            # Teeth (white points)
            pygame.draw.polygon(self._screen, (250, 250, 250), [(rect.left + 7, rect.centery - 6), (rect.left + 9, rect.centery - 2), (rect.left + 11, rect.centery - 6)])
            pygame.draw.polygon(self._screen, (250, 250, 250), [(rect.left + 15, rect.centery - 6), (rect.left + 17, rect.centery - 2), (rect.left + 19, rect.centery - 6)])
            pygame.draw.polygon(self._screen, (250, 250, 250), [(rect.left + 11, rect.centery + 3), (rect.left + 13, rect.centery - 1), (rect.left + 15, rect.centery + 3)])
            
            # Hanging pink tongue
            pygame.draw.ellipse(self._screen, (230, 80, 130), (rect.centerx - 2, rect.centery - 3, 6, 10))
        else:
            # Threat marker dot
            pygame.draw.circle(self._screen, color, rect.center, 8)

    def _draw_player_sprite(self, rect: pygame.Rect, color: tuple[int, int, int], enchanted: bool, player: Player = None):
        # Glow ring if enchanted
        if enchanted:
            pygame.draw.circle(self._screen, (240, 200, 30), rect.center, 13, 2)

        char_class = "Wizard"
        if player and hasattr(player, "char_class"):
            char_class = player.char_class

        # Draw animated spritesheet if loaded (for Knight class only)
        if char_class == "Knight" and self._spritesheet and player:
            dir_rows = {"DOWN": 0, "UP": 1, "LEFT": 2, "RIGHT": 3}
            row = dir_rows.get(player.facing, 0)
            
            # Check if moving to advance walk frame
            is_moving = False
            if player in self._entity_positions:
                vx, vy = self._entity_positions[player]
                tx, ty = player.x * TILE_SIZE, player.y * TILE_SIZE
                is_moving = (math.hypot(tx - vx, ty - vy) > 0.5)
                
            frame_idx = 0
            if is_moving:
                frame_idx = (self._frame_count // 6) % 4
                
            src_rect = pygame.Rect(frame_idx * 32, row * 32, 32, 32)
            self._screen.blit(self._spritesheet, rect.topleft, src_rect)
            return

        # Fallback vector sprites for classes
        if char_class == "Knight":
            # Plate armor chestplate
            pygame.draw.rect(self._screen, (130, 130, 140), (rect.centerx - 7, rect.centery - 2, 14, 11), border_radius=2)
            # Steel Helmet
            pygame.draw.circle(self._screen, (170, 170, 180), (rect.centerx, rect.centery - 6), 6)
            # Visor slot
            pygame.draw.rect(self._screen, (35, 35, 40), (rect.centerx - 4, rect.centery - 7, 8, 2))
            # Red plume
            pygame.draw.circle(self._screen, (220, 40, 40), (rect.centerx, rect.top + 5), 2)
            # Wooden shield on arm
            pygame.draw.polygon(self._screen, (139, 69, 19), [
                (rect.centerx - 11, rect.centery + 1),
                (rect.centerx - 6, rect.centery + 1),
                (rect.centerx - 8, rect.centery + 8)
            ])
            pygame.draw.polygon(self._screen, (235, 180, 25), [
                (rect.centerx - 11, rect.centery + 1),
                (rect.centerx - 6, rect.centery + 1),
                (rect.centerx - 8, rect.centery + 8)
            ], width=1)
        elif char_class == "Rogue":
            # Green Rogue drawing
            # Cloak forest green
            pygame.draw.circle(self._screen, (34, 110, 56), rect.center, 8)
            # Dark cowl/hood
            pygame.draw.circle(self._screen, (45, 55, 50), (rect.centerx, rect.centery - 4), 6)
            # Shadowy mask inside cowl
            pygame.draw.circle(self._screen, (20, 22, 20), (rect.centerx, rect.centery - 4), 4)
            # Glinting eyes
            pygame.draw.circle(self._screen, (180, 220, 255), (rect.centerx - 1, rect.centery - 4.5), 1)
            pygame.draw.circle(self._screen, (180, 220, 255), (rect.centerx + 1, rect.centery - 4.5), 1)
            # Steel dagger in hand
            pygame.draw.line(self._screen, (200, 200, 205), (rect.centerx + 5, rect.centery), (rect.centerx + 10, rect.centery - 5), 2)
            pygame.draw.line(self._screen, (120, 80, 40), (rect.centerx + 4, rect.centery + 1), (rect.centerx + 6, rect.centery - 1), 2)
        else:
            # Wizard Cloak (deep purple circle)
            pygame.draw.circle(self._screen, (100, 45, 175), rect.center, 9)
            # Gold emblem/star on cloak
            pygame.draw.circle(self._screen, (245, 205, 35), (rect.centerx, rect.centery + 2), 2)

            # Conical Wizard Hat
            hat_points = [
                (rect.centerx, rect.top + 3),
                (rect.centerx - 8, rect.centery - 2),
                (rect.centerx + 8, rect.centery - 2)
            ]
            pygame.draw.polygon(self._screen, (25, 45, 120), hat_points)
            # Yellow brim
            pygame.draw.line(self._screen, (245, 205, 35), (rect.centerx - 10, rect.centery - 2), (rect.centerx + 10, rect.centery - 2), 2)

    def _draw_projectiles(self, shake_x: int, shake_y: int):
        for proj in self._projectiles:
            path = proj["path"]
            idx = int(proj["index"])
            if idx >= len(path) - 1:
                continue
            
            frac = proj["index"] - idx
            t1 = path[idx]
            t2 = path[idx + 1]
            px = (t1[0] + (t2[0] - t1[0]) * frac + 0.5) * TILE_SIZE + shake_x
            py = (t1[1] + (t2[1] - t1[1]) * frac + 0.5) * TILE_SIZE + shake_y
            
            ptype = proj.get("type", "lightning")
            if ptype == "lightning":
                # Compute starting point (player position)
                dx = path[1][0] - path[0][0] if len(path) > 1 else 0
                dy = path[1][1] - path[0][1] if len(path) > 1 else 0
                
                player_x = (path[0][0] - dx + 0.5) * TILE_SIZE + shake_x
                player_y = (path[0][1] - dy + 0.5) * TILE_SIZE + shake_y
                
                # Draw crackling electrical bolt segments from player to current tip (px, py)
                points = [(player_x, player_y)]
                dist = math.hypot(px - player_x, py - player_y)
                num_segments = max(4, int(dist / 8))
                
                for i in range(1, num_segments):
                    t = i / num_segments
                    lx = player_x + (px - player_x) * t
                    ly = player_y + (py - player_y) * t
                    
                    # Add randomized offset perpendicular to direction
                    line_dx = px - player_x
                    line_dy = py - player_y
                    line_len = math.hypot(line_dx, line_dy)
                    if line_len > 0:
                        nx = -line_dy / line_len
                        ny = line_dx / line_len
                        offset = random.uniform(-6, 6)
                        lx += nx * offset
                        ly += ny * offset
                    points.append((lx, ly))
                points.append((px, py))
                
                if len(points) >= 2:
                    # Thick light blue outer glow
                    pygame.draw.lines(self._screen, (100, 200, 255), False, points, 4)
                    # Thin white core
                    pygame.draw.lines(self._screen, (255, 255, 255), False, points, 2)
            else:
                # Fireball core
                pygame.draw.circle(self._screen, (255, 230, 40), (int(px), int(py)), 8)
                pygame.draw.circle(self._screen, (240, 60, 20), (int(px), int(py)), 5)
                pygame.draw.circle(self._screen, (255, 255, 255), (int(px), int(py)), 2)

    def _draw_particles(self, shake_x: int, shake_y: int):
        for p in self._particles:
            alpha = int(max(0, min(255, (p["life"] / p["max_life"]) * 255)))
            color_with_alpha = p["color"] + (alpha,)
            
            # Temporary surface for transparent particles
            surf = pygame.Surface((p["size"] * 2, p["size"] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color_with_alpha, (p["size"], p["size"]), p["size"])
            
            self._screen.blit(surf, (p["x"] - p["size"] + shake_x, p["y"] - p["size"] + shake_y))

    def _draw_damage_texts(self, shake_x: int, shake_y: int):
        for dt in self._damage_texts:
            alpha = int(max(0, min(255, (dt["life"] / dt["max_life"]) * 255)))
            
            # Generate styled text surface
            txt_surf = self._header_font.render(dt["text"], True, dt["color"])
            
            # Alpha blitting using a temporary surface
            alpha_surf = pygame.Surface(txt_surf.get_size(), pygame.SRCALPHA)
            alpha_surf.fill((255, 255, 255, alpha))
            alpha_surf.blit(txt_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            # Center text above character tile
            tx = dt["x"] - alpha_surf.get_width() // 2 + shake_x
            ty = dt["y"] - 15 + shake_y
            self._screen.blit(alpha_surf, (tx, ty))

    def _draw_sidebar(self, player: Player):
        sx = MAP_PIXEL_WIDTH
        
        # Sidebar Panel Divider / Panel Background
        pygame.draw.rect(self._screen, (20, 20, 26), (sx, 0, SIDEBAR_WIDTH, TOTAL_HEIGHT))
        pygame.draw.line(self._screen, (40, 40, 50), (sx, 0), (sx, TOTAL_HEIGHT), 2)

        # Header Status
        self._draw_text(sx + 20, 20, "-- STATUS --", color_rgb(Color.YELLOW), font=self._header_font)
        self._draw_text(sx + 20, 48, f"Class: {getattr(player, 'char_class', 'Wizard')}", color_rgb(Color.CYAN), font=self._header_font)
        self._draw_text(sx + 20, 76, f"Depth: {player.depth} (max {player.max_depth})", color_rgb(Color.WHITE))

        # HP bar
        self._draw_text(sx + 20, 106, "HP: ", color_rgb(Color.WHITE))
        hp_ratio = player.hp / player.max_hp
        bar_w = 180
        bar_h = 16
        bx = sx + 60
        by = 106
        
        # Border box
        pygame.draw.rect(self._screen, (45, 45, 50), (bx, by, bar_w, bar_h), border_radius=3)
        
        # Fill ratio color
        if hp_ratio <= 0.33:
            fill_c = color_rgb(Color.RED)
        elif hp_ratio <= 0.66:
            fill_c = color_rgb(Color.YELLOW)
        else:
            fill_c = color_rgb(Color.GREEN)
            
        if player.hp > 0:
            fill_w = max(4, int(bar_w * hp_ratio))
            pygame.draw.rect(self._screen, fill_c, (bx, by, fill_w, bar_h), border_radius=3)
            
        # Numerical HP values on top of bar
        txt_hp = f"{player.hp}/{player.max_hp}"
        hp_surf = self._ui_font.render(txt_hp, True, (255, 255, 255))
        self._screen.blit(hp_surf, (bx + (bar_w - hp_surf.get_width()) // 2, by - 1))

        # Status text details
        self._draw_text(sx + 20, 136, f"ATK:   {player.attack}", color_rgb(Color.WHITE))
        self._draw_text(sx + 20, 166, f"Kills: {player.kills}", color_rgb(Color.WHITE))
        self._draw_text(sx + 20, 196, f"Gold:  {player.coins}", (240, 195, 30), font=self._header_font)
        self._draw_text(sx + 20, 226, f"Score: {player.score}", color_rgb(Color.CYAN), font=self._header_font)

        # Keyboard Controls Cheat Sheet
        self._draw_text(sx + 20, 260, "-- CONTROLS --", color_rgb(Color.YELLOW), font=self._header_font)
        controls = [
            ("Arrows", "Move / Bump Attack"),
            ("G Key", "Pick up item"),
            ("I Key", "Open Inventory"),
            ("Z Key", "Zap wand (+ Arrow)"),
            ("Enter", "Use stairs"),
            ("Q Key", "Quit game"),
        ]
        curr_y = 290
        for key, desc in controls:
            self._draw_text(sx + 20, curr_y, f"{key:6}: {desc}", color_rgb(Color.GRAY))
            curr_y += 24

        # Equipment slots panel
        pygame.draw.line(self._screen, (35, 35, 45), (sx + 15, curr_y + 10), (sx + SIDEBAR_WIDTH - 15, curr_y + 10))
        curr_y += 25
        
        self._draw_text(sx + 20, curr_y, "Weapon Slot:", color_rgb(Color.YELLOW))
        weapon_name = player.inventory.equipped_weapon.display_name if player.inventory.equipped_weapon else "(fists)"
        self._draw_text(sx + 20, curr_y + 24, weapon_name, color_rgb(Color.CYAN), font=self._header_font)
        
        self._draw_text(sx + 20, curr_y + 55, "Wand Slot:", color_rgb(Color.YELLOW))
        wand_name = player.inventory.equipped_wand.display_name if player.inventory.equipped_wand else "(none)"
        self._draw_text(sx + 20, curr_y + 79, wand_name, color_rgb(Color.MAGENTA), font=self._header_font)

    def _draw_log(self, log: MessageLog):
        y_top = MAP_PIXEL_HEIGHT
        
        # Message log border separator
        pygame.draw.rect(self._screen, (10, 10, 14), (0, y_top, MAP_PIXEL_WIDTH, LOG_HEIGHT))
        pygame.draw.line(self._screen, (40, 40, 50), (0, y_top), (MAP_PIXEL_WIDTH, y_top), 2)
        
        # Render rolling text messages
        row = 0
        curr_y = y_top + 12
        for text, color in log.recent:
            if row >= 5:
                break
            self._draw_text(15, curr_y, text, color_rgb(color), font=self._log_font)
            curr_y += 24
            row += 1

    def _draw_text(self, x: int, y: int, text: str, color: tuple[int, int, int], font=None):
        if font is None:
            font = self._ui_font
        surf = font.render(text, True, color)
        self._screen.blit(surf, (x, y))

    def _draw_inventory_overlay(self, player: Player):
        # Create dark translucent screen overlay surface
        overlay = pygame.Surface((TOTAL_WIDTH, TOTAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self._screen.blit(overlay, (0, 0))

        # Modal Panel rect
        w, h = 540, 420
        mx = (MAP_PIXEL_WIDTH - w) // 2
        my = (MAP_PIXEL_HEIGHT - h) // 2
        modal_rect = pygame.Rect(mx, my, w, h)
        
        # Modal shadow / border
        pygame.draw.rect(self._screen, (22, 25, 36), modal_rect, border_radius=8)
        pygame.draw.rect(self._screen, color_rgb(Color.CYAN), modal_rect, width=2, border_radius=8)

        # Inventory details header
        self._draw_text(mx + 25, my + 20, "-- INVENTORY --", color_rgb(Color.YELLOW), font=self._header_font)
        self._draw_text(mx + 25, my + 45, "Press an item letter [ a - t ] to equip or use, or any other key to cancel", color_rgb(Color.GRAY))
        pygame.draw.line(self._screen, (40, 45, 60), (mx + 20, my + 75), (mx + w - 20, my + 75), 2)

        items = player.inventory.items
        if not items:
            self._draw_text(mx + 200, my + 180, "(empty backpack)", color_rgb(Color.GRAY), font=self._header_font)
        else:
            col_w = (w - 60) // 2
            row_h = 28
            max_rows = 10
            
            for i, item in enumerate(items):
                letter = chr(ord("a") + i)
                col = i // max_rows
                row = i % max_rows
                
                item_x = mx + 25 + col * (col_w + 20)
                item_y = my + 90 + row * row_h
                
                # Check item parameters
                if item.kind.value == "healing_potion":
                    detail = f"heals {item.heal_amount}"
                elif item.kind.value == "weapon":
                    detail = f"+{item.attack_bonus} atk"
                elif item.kind.value == "wand":
                    detail = f"{item.wand_damage} dmg, {item.charges} chg"
                elif item.kind.value == "key":
                    detail = "opens locked chests"
                else:
                    detail = ""

                equipped = ""
                is_equipped = (item is player.inventory.equipped_weapon or item is player.inventory.equipped_wand)
                if is_equipped:
                    equipped = " (equipped)"
                
                # Render item slot box
                slot_rect = pygame.Rect(item_x, item_y, col_w, row_h - 4)
                bg_color = (35, 45, 75) if is_equipped else (26, 30, 45)
                border_color = color_rgb(Color.GREEN) if is_equipped else (45, 50, 70)
                pygame.draw.rect(self._screen, bg_color, slot_rect, border_radius=4)
                pygame.draw.rect(self._screen, border_color, slot_rect, width=1, border_radius=4)

                # Hotkey indicator label
                key_surf = self._header_font.render(f" {letter.upper()} ", True, color_rgb(Color.YELLOW))
                pygame.draw.rect(self._screen, (20, 22, 32), (item_x + 4, item_y + 3, 20, 18), border_radius=2)
                self._screen.blit(key_surf, (item_x + 6, item_y + 2))

                # Item name and details text
                item_c = color_rgb(item.color)
                name_surf = self._ui_font.render(item.display_name, True, item_c)
                self._screen.blit(name_surf, (item_x + 30, item_y + 3))

                detail_c = color_rgb(Color.GREEN) if is_equipped else color_rgb(Color.GRAY)
                detail_surf = self._ui_font.render(f" [{detail}]{equipped}", True, detail_c)
                self._screen.blit(detail_surf, (item_x + 30 + name_surf.get_width(), item_y + 3))

    def _draw_shop_overlay(self, player: Player, merchant):
        # Create dark translucent screen overlay surface
        overlay = pygame.Surface((TOTAL_WIDTH, TOTAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self._screen.blit(overlay, (0, 0))

        # Modal Panel rect
        w, h = 540, 436
        mx = (MAP_PIXEL_WIDTH - w) // 2
        my = (MAP_PIXEL_HEIGHT - h) // 2
        modal_rect = pygame.Rect(mx, my, w, h)
        
        # Modal shadow / border (warm wood theme)
        pygame.draw.rect(self._screen, (28, 22, 16), modal_rect, border_radius=8)
        pygame.draw.rect(self._screen, (235, 180, 25), modal_rect, width=2, border_radius=8)

        # Header Title
        self._draw_text(mx + 25, my + 20, "-- MERCHANT SHOP --", (235, 180, 25), font=self._header_font)
        self._draw_text(mx + 25, my + 45, "Keys [ 1 - 4 ] or [ a - d ] to purchase. ESC to exit.", (180, 180, 180))
        
        # Player Gold
        gold_text = f"Your Gold: {player.coins}g"
        gold_surf = self._header_font.render(gold_text, True, (235, 180, 25))
        self._screen.blit(gold_surf, (mx + w - gold_surf.get_width() - 25, my + 20))
        
        pygame.draw.line(self._screen, (65, 50, 40), (mx + 20, my + 75), (mx + w - 20, my + 75), 2)

        # 4 Shop Slots
        for i in range(4):
            item, price, is_sold_out = merchant.shop_items[i]
            
            slot_x = mx + 20
            slot_y = my + 90 + i * 80
            slot_w = w - 40
            slot_h = 70
            slot_rect = pygame.Rect(slot_x, slot_y, slot_w, slot_h)
            
            # Select colors based on status
            if is_sold_out:
                bg_color = (18, 16, 15)
                border_color = (45, 40, 38)
            else:
                bg_color = (36, 30, 26)
                border_color = (65, 52, 42)
                
            pygame.draw.rect(self._screen, bg_color, slot_rect, border_radius=6)
            pygame.draw.rect(self._screen, border_color, slot_rect, width=1, border_radius=6)
            
            # Key indicator button (e.g. "1")
            key_box_rect = pygame.Rect(slot_x + 10, slot_y + 15, 24, 24)
            pygame.draw.rect(self._screen, (24, 20, 18), key_box_rect, border_radius=4)
            pygame.draw.rect(self._screen, (235, 180, 25) if not is_sold_out else (100, 100, 100), key_box_rect, width=1, border_radius=4)
            
            key_surf = self._header_font.render(str(i + 1), True, (235, 180, 25) if not is_sold_out else (120, 120, 120))
            self._screen.blit(key_surf, (key_box_rect.centerx - key_surf.get_width() // 2, key_box_rect.centery - key_surf.get_height() // 2))
            
            # Render item sprite next to key label
            icon_rect = pygame.Rect(slot_x + 45, slot_y + (slot_h - 32) // 2, 32, 32)
            icon_color = color_rgb(item.color)
            if is_sold_out:
                icon_color = (80, 80, 80)
            
            if item.name == "bless weapon":
                # Draw a glowing yellow star / sparkle
                star_color = (255, 215, 0) if not is_sold_out else (80, 80, 80)
                pygame.draw.circle(self._screen, star_color, icon_rect.center, 5)
                pygame.draw.line(self._screen, star_color, (icon_rect.centerx - 10, icon_rect.centery), (icon_rect.centerx + 10, icon_rect.centery), 2)
                pygame.draw.line(self._screen, star_color, (icon_rect.centerx, icon_rect.centery - 10), (icon_rect.centerx, icon_rect.centery + 10), 2)
            elif item.kind.value == "healing_potion":
                self._draw_potion(icon_rect, icon_color)
            elif item.kind.value == "weapon":
                self._draw_weapon(icon_rect, icon_color)
            elif item.kind.value == "wand":
                self._draw_wand(icon_rect, icon_color)
                
            # Item Name
            item_name = item.display_name.capitalize()
            name_color = color_rgb(item.color) if not is_sold_out else (120, 120, 120)
            name_surf = self._header_font.render(item_name, True, name_color)
            self._screen.blit(name_surf, (slot_x + 90, slot_y + 12))
            
            # Item description
            if item.name == "bless weapon":
                desc = "Blesses equipped weapon. Needed to harm the boss."
            elif item.kind.value == "healing_potion":
                desc = f"Restores {item.heal_amount} HP. Consumed from inventory."
            elif item.kind.value == "weapon":
                desc = f"Melee weapon: provides +{item.attack_bonus} attack bonus."
            elif item.kind.value == "wand":
                desc = f"Ranged zap. Pierces. Deals {item.wand_damage} dmg. {item.charges} chg."
            else:
                desc = ""
                
            desc_color = (180, 180, 180) if not is_sold_out else (100, 100, 100)
            desc_surf = self._ui_font.render(desc, True, desc_color)
            self._screen.blit(desc_surf, (slot_x + 90, slot_y + 40))
            
            # Price / Sold out
            if is_sold_out:
                price_text = "[ SOLD OUT ]"
                price_color = (180, 50, 50)
            else:
                price_text = f"{price}g"
                price_color = (255, 215, 0)
                
            price_surf = self._header_font.render(price_text, True, price_color)
            self._screen.blit(price_surf, (slot_x + slot_w - price_surf.get_width() - 20, slot_y + (slot_h - price_surf.get_height()) // 2))

    def render_title_screen(self, highscores):
        self._screen.fill((10, 10, 14))

        # Draw procedural background sparkles
        for _ in range(30):
            x = random.randint(10, TOTAL_WIDTH - 10)
            y = random.randint(10, TOTAL_HEIGHT - 10)
            size = random.choice([1, 2])
            pygame.draw.circle(self._screen, (60, 60, 80), (x, y), size)

        # Big Title Logo
        t_surf = self._title_font.render("WIZARD'S DUNGEON", True, color_rgb(Color.YELLOW))
        self._screen.blit(t_surf, ((TOTAL_WIDTH - t_surf.get_width()) // 2, 80))
        
        st_surf = self._header_font.render("A Graphical Pygame Roguelike Quest", True, color_rgb(Color.CYAN))
        self._screen.blit(st_surf, ((TOTAL_WIDTH - st_surf.get_width()) // 2, 140))

        # Draw a line divider
        pygame.draw.line(self._screen, (40, 50, 75), (TOTAL_WIDTH // 4, 180), (TOTAL_WIDTH * 3 // 4, 180), 2)

        # Highscores panel centered
        hs_x = (TOTAL_WIDTH - 400) // 2
        self._draw_text(hs_x, 220, "--- HIGH SCORES ---", color_rgb(Color.YELLOW), font=self._header_font)
        
        curr_y = 260
        if not highscores:
            self._draw_text(hs_x + 100, curr_y + 40, "(no runs recorded yet)", color_rgb(Color.GRAY))
        else:
            for rank, entry in enumerate(highscores[:8], start=1):
                score, depth, kills, date_obj = entry
                txt = f"{rank:>2}. Score: {score:>5} | Depth: {depth:>2} | Kills: {kills:>3}"
                self._draw_text(hs_x, curr_y, txt, color_rgb(Color.WHITE))
                curr_y += 26

        # Prompts at bottom
        p_surf = self._header_font.render("Press ENTER to Begin the Quest", True, color_rgb(Color.GREEN))
        # Add pulsing bounce effect
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
        pulse_color = (int(46 + (209 - 46) * pulse), int(196 + (255 - 196) * pulse), int(120 + (240 - 120) * pulse))
        p_surf = self._header_font.render("Press ENTER to Begin the Quest", True, pulse_color)
        
        self._screen.blit(p_surf, ((TOTAL_WIDTH - p_surf.get_width()) // 2, 600))
        
        exit_surf = self._ui_font.render("Press Q to Quit", True, color_rgb(Color.GRAY))
        self._screen.blit(exit_surf, ((TOTAL_WIDTH - exit_surf.get_width()) // 2, 640))

        pygame.display.flip()

    def render_class_select(self, selected_class_idx: int):
        self._screen.fill((10, 10, 14))

        # Background sparkles
        for _ in range(30):
            x = random.randint(10, TOTAL_WIDTH - 10)
            y = random.randint(10, TOTAL_HEIGHT - 10)
            size = random.choice([1, 2])
            pygame.draw.circle(self._screen, (60, 60, 80), (x, y), size)

        # Main Title Header
        title_surf = self._title_font.render("SELECT YOUR HERO CLASS", True, color_rgb(Color.YELLOW))
        self._screen.blit(title_surf, ((TOTAL_WIDTH - title_surf.get_width()) // 2, 70))

        # 3 Class Cards Setup
        classes_data = [
            {
                "name": "KNIGHT",
                "hp": "Max HP: 40",
                "weapon": "Weapon: Shortsword (+2 ATK)",
                "desc": [
                    "A heavily armored veteran.",
                    "Starts with a Shortsword.",
                    "Plate armor blocks 1 damage",
                    "from all monster attacks."
                ],
                "color": (200, 200, 210),
                "key_hint": "Press 1 / K to Select"
            },
            {
                "name": "WIZARD",
                "hp": "Max HP: 20",
                "weapon": "Weapon: Wand of Lightning",
                "desc": [
                    "Master of arcane forces.",
                    "Starts with a readied",
                    "Wand of Lightning that",
                    "charges slowly over time."
                ],
                "color": (155, 80, 230),
                "key_hint": "Press 2 / W to Select"
            },
            {
                "name": "ROGUE",
                "hp": "Max HP: 30",
                "weapon": "Weapon: Dagger (+1 ATK)",
                "desc": [
                    "A swift, deadly shadow.",
                    "Moves faster (6-frame CD).",
                    "Dagger attacks have a 30%",
                    "chance for double CRIT."
                ],
                "color": (46, 196, 120),
                "key_hint": "Press 3 / R to Select"
            }
        ]

        card_w, card_h = 320, 380
        card_y = 160
        gap = 40
        start_x = (TOTAL_WIDTH - (3 * card_w + 2 * gap)) // 2

        for idx, data in enumerate(classes_data):
            card_x = start_x + idx * (card_w + gap)
            card_rect = pygame.Rect(card_x, card_y, card_w, card_h)

            selected = (idx == selected_class_idx)
            
            # Select background and border colors
            if selected:
                bg_color = (36, 30, 26)
                border_color = (255, 215, 0)
                border_width = 3
            else:
                bg_color = (18, 18, 22)
                border_color = (60, 60, 65)
                border_width = 1

            pygame.draw.rect(self._screen, bg_color, card_rect, border_radius=8)
            pygame.draw.rect(self._screen, border_color, card_rect, width=border_width, border_radius=8)

            # Title
            name_surf = self._header_font.render(data["name"], True, border_color if selected else (200, 200, 200))
            self._screen.blit(name_surf, (card_x + (card_w - name_surf.get_width()) // 2, card_y + 20))

            # Stats (HP and Weapon)
            hp_surf = self._ui_font.render(data["hp"], True, (255, 255, 255))
            self._screen.blit(hp_surf, (card_x + (card_w - hp_surf.get_width()) // 2, card_y + 55))
            
            wpn_surf = self._ui_font.render(data["weapon"], True, color_rgb(Color.CYAN))
            self._screen.blit(wpn_surf, (card_x + (card_w - wpn_surf.get_width()) // 2, card_y + 75))

            # Vector illustrations in center
            icon_center_x = card_x + card_w // 2
            icon_center_y = card_y + 160
            
            if data["name"] == "KNIGHT":
                # Knight visual
                # Plate body
                pygame.draw.rect(self._screen, (130, 130, 140), (icon_center_x - 14, icon_center_y - 2, 28, 22), border_radius=4)
                # Helmet
                pygame.draw.circle(self._screen, (170, 170, 180), (icon_center_x, icon_center_y - 12), 12)
                # Visor slot
                pygame.draw.rect(self._screen, (35, 35, 40), (icon_center_x - 8, icon_center_y - 14, 16, 3))
                # Red plume
                pygame.draw.circle(self._screen, (220, 40, 40), (icon_center_x, icon_center_y - 28), 5)
                # Wooden shield
                pygame.draw.polygon(self._screen, (139, 69, 19), [
                    (icon_center_x - 24, icon_center_y + 4),
                    (icon_center_x - 14, icon_center_y + 4),
                    (icon_center_x - 19, icon_center_y + 18)
                ])
                pygame.draw.polygon(self._screen, (235, 180, 25), [
                    (icon_center_x - 24, icon_center_y + 4),
                    (icon_center_x - 14, icon_center_y + 4),
                    (icon_center_x - 19, icon_center_y + 18)
                ], width=1)
                
            elif data["name"] == "WIZARD":
                # Wizard visual
                # Purple cloak
                pygame.draw.circle(self._screen, (100, 45, 175), (icon_center_x, icon_center_y), 15)
                # Gold emblem
                pygame.draw.circle(self._screen, (245, 205, 35), (icon_center_x, icon_center_y + 3), 3)
                # Conical Hat
                hat_points = [
                    (icon_center_x, icon_center_y - 36),
                    (icon_center_x - 13, icon_center_y - 6),
                    (icon_center_x + 13, icon_center_y - 6)
                ]
                pygame.draw.polygon(self._screen, (25, 45, 120), hat_points)
                # Yellow brim
                pygame.draw.line(self._screen, (245, 205, 35), (icon_center_x - 16, icon_center_y - 6), (icon_center_x + 16, icon_center_y - 6), 3)
                
            elif data["name"] == "ROGUE":
                # Rogue visual
                # Cloak forest green
                pygame.draw.circle(self._screen, (34, 110, 56), (icon_center_x, icon_center_y), 14)
                # Dark hood
                pygame.draw.circle(self._screen, (45, 55, 50), (icon_center_x, icon_center_y - 6), 10)
                # Face shadow
                pygame.draw.circle(self._screen, (20, 22, 20), (icon_center_x, icon_center_y - 6), 7)
                # Glinting blue eyes
                pygame.draw.circle(self._screen, (180, 220, 255), (icon_center_x - 3, icon_center_y - 7), 1.5)
                pygame.draw.circle(self._screen, (180, 220, 255), (icon_center_x + 3, icon_center_y - 7), 1.5)
                # Dagger (steel blade, brown hilt)
                pygame.draw.line(self._screen, (200, 200, 205), (icon_center_x + 10, icon_center_y + 2), (icon_center_x + 20, icon_center_y - 8), 3)
                pygame.draw.line(self._screen, (120, 80, 40), (icon_center_x + 8, icon_center_y + 4), (icon_center_x + 11, icon_center_y + 1), 3)

            # Descriptions stacked vertically
            desc_y = card_y + 230
            for desc_line in data["desc"]:
                d_surf = self._ui_font.render(desc_line, True, (170, 170, 175))
                self._screen.blit(d_surf, (card_x + (card_w - d_surf.get_width()) // 2, desc_y))
                desc_y += 20

            # Direct hotkey binding info at bottom of card
            k_surf = self._ui_font.render(data["key_hint"], True, color_rgb(Color.GRAY))
            self._screen.blit(k_surf, (card_x + (card_w - k_surf.get_width()) // 2, card_y + 345))

        # Instructions / Navigation Prompt
        nav_text = "Use LEFT / RIGHT arrows or A / D to navigate. Press ENTER to select."
        nav_surf = self._header_font.render(nav_text, True, color_rgb(Color.GREEN))
        self._screen.blit(nav_surf, ((TOTAL_WIDTH - nav_surf.get_width()) // 2, 560))
        
        esc_surf = self._ui_font.render("Press ESC to return to Title Screen", True, color_rgb(Color.GRAY))
        self._screen.blit(esc_surf, ((TOTAL_WIDTH - esc_surf.get_width()) // 2, 600))

        pygame.display.flip()

    def render_game_over(self, player: Player, highscores: list):
        self._screen.fill((15, 10, 10))

        # Title
        go_surf = self._title_font.render("GAME OVER", True, color_rgb(Color.RED))
        self._screen.blit(go_surf, ((TOTAL_WIDTH - go_surf.get_width()) // 2, 70))

        # Final Score stats
        self._draw_text(TOTAL_WIDTH // 4, 150, f"Max depth reached:  {player.max_depth}", color_rgb(Color.WHITE), font=self._header_font)
        self._draw_text(TOTAL_WIDTH // 4, 185, f"Monsters defeated:  {player.kills}", color_rgb(Color.WHITE), font=self._header_font)
        self._draw_text(TOTAL_WIDTH // 4, 220, f"Final score:        {player.score}", color_rgb(Color.CYAN), font=self._header_font)

        pygame.draw.line(self._screen, (85, 30, 30), (TOTAL_WIDTH // 4, 265), (TOTAL_WIDTH * 3 // 4, 265), 2)

        # Rankings high score table
        hs_x = (TOTAL_WIDTH - 440) // 2
        self._draw_text(hs_x, 290, "-- HIGH SCORE LEADERBOARD --", color_rgb(Color.YELLOW), font=self._header_font)
        
        curr_y = 330
        for rank, s in enumerate(highscores[:10], start=1):
            # Try to identify which entry was the current run (by matching values, date-match is best)
            # Since highscores contains scores directly, let's highlight entry rank
            is_current = (s[0] == player.score and s[1] == player.max_depth and s[2] == player.kills)
            
            color = color_rgb(Color.CYAN) if is_current else color_rgb(Color.GRAY)
            marker = " *" if is_current else "  "
            
            txt = f"{rank:>2}.{marker}Score: {s[0]:>5}   Depth: {s[1]:>2}   Kills: {s[2]:>3}"
            self._draw_text(hs_x, curr_y, txt, color, font=self._ui_font)
            curr_y += 24

        # Exit prompt
        exit_surf = self._header_font.render("Press ANY KEY to Return to Title Screen", True, color_rgb(Color.YELLOW))
        self._screen.blit(exit_surf, ((TOTAL_WIDTH - exit_surf.get_width()) // 2, 620))

        pygame.display.flip()
