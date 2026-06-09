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

    def add_projectile(self, path: list[tuple[int, int]], callback):
        self._projectiles.append({
            "path": path,
            "index": 0.0,
            "speed": 0.35,  # tiles per frame
            "callback": callback
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
            if idx < len(path) - 1:
                frac = proj["index"] - idx
                t1 = path[idx]
                t2 = path[idx + 1]
                px = (t1[0] + (t2[0] - t1[0]) * frac + 0.5) * TILE_SIZE
                py = (t1[1] + (t2[1] - t1[1]) * frac + 0.5) * TILE_SIZE
                # Trail smoke particle
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
                # Spawn explosion particles at the destination
                dest = path[-1]
                self.add_particles(dest[0], dest[1], (230, 55, 55), count=18)
                self.add_particles(dest[0], dest[1], (235, 195, 45), count=12)
                self.trigger_shake(8.0)
                # Run complete callback
                proj["callback"]()

    def render(self, level: DungeonLevel, player: Player, log: MessageLog, show_inventory=False):
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
            else:
                # Fallback circular pouch item
                pygame.draw.circle(self._screen, color, rect.center, 6)

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
        else:
            # Threat marker dot
            pygame.draw.circle(self._screen, color, rect.center, 8)

    def _draw_player_sprite(self, rect: pygame.Rect, color: tuple[int, int, int], enchanted: bool, player: Player = None):
        # Glow ring if enchanted
        if enchanted:
            pygame.draw.circle(self._screen, (240, 200, 30), rect.center, 13, 2)

        # Draw animated spritesheet if loaded
        if self._spritesheet and player:
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

        # Wizard Cloak (deep purple circle) fallback
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
            
            # Draw fire core
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
        self._draw_text(sx + 20, 50, f"Depth: {player.depth} (max {player.max_depth})", color_rgb(Color.WHITE))

        # HP bar
        self._draw_text(sx + 20, 80, "HP: ", color_rgb(Color.WHITE))
        hp_ratio = player.hp / player.max_hp
        bar_w = 180
        bar_h = 16
        bx = sx + 60
        by = 80
        
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
        self._draw_text(sx + 20, 110, f"ATK:   {player.attack}", color_rgb(Color.WHITE))
        self._draw_text(sx + 20, 140, f"Kills: {player.kills}", color_rgb(Color.WHITE))
        self._draw_text(sx + 20, 170, f"Score: {player.score}", color_rgb(Color.CYAN), font=self._header_font)

        # Keyboard Controls Cheat Sheet
        self._draw_text(sx + 20, 220, "-- CONTROLS --", color_rgb(Color.YELLOW), font=self._header_font)
        controls = [
            ("Arrows", "Move / Bump Attack"),
            ("G Key", "Pick up item"),
            ("I Key", "Open Inventory"),
            ("Z Key", "Zap wand (+ Arrow)"),
            ("> Key", "Descend stairs"),
            ("< Key", "Ascend stairs"),
            ("Q Key", "Quit game"),
        ]
        curr_y = 250
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
