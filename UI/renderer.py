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

# Atari-like arcade palette anchors.
ATARI_BG = (8, 12, 22)
ATARI_PANEL = (14, 20, 34)
ATARI_PANEL_BORDER = (42, 78, 132)
ATARI_NEON_CYAN = (84, 198, 255)
ATARI_NEON_YELLOW = (248, 208, 74)
ATARI_NEON_ORANGE = (238, 126, 46)
ATARI_PURPLE = (92, 66, 166)


class RetroFont:
    """Renders text the way an 80s DOS machine would: a fixed-width font drawn
    at a small base size with anti-aliasing OFF (so each glyph is just a pixel
    grid), then blown up by an integer factor with nearest-neighbor scaling so
    every pixel becomes a fat square block. Results are cached since UI strings
    repeat every frame."""

    def __init__(self, name, base_size, scale=2, bold=False):
        try:
            self._font = pygame.font.SysFont(name, base_size, bold=bold)
        except Exception:
            self._font = pygame.font.SysFont(None, base_size, bold=bold)
        self._scale = scale
        self._cache = {}

    def render(self, text, _aa, color):
        key = (text, tuple(color))
        surf = self._cache.get(key)
        if surf is None:
            base = self._font.render(text, False, color)  # antialias OFF
            if self._scale != 1 and base.get_width() > 0 and base.get_height() > 0:
                surf = pygame.transform.scale(
                    base, (base.get_width() * self._scale,
                           base.get_height() * self._scale))  # nearest -> chunky
            else:
                surf = base
            if len(self._cache) < 512:
                self._cache[key] = surf
        return surf

    def size(self, text):
        w, h = self._font.size(text)
        return (w * self._scale, h * self._scale)


class Renderer:
    def __init__(self):
        # Initialize pygame display
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        self._screen = pygame.display.set_mode((TOTAL_WIDTH, TOTAL_HEIGHT))
        pygame.display.set_caption("Rogue PyGame - Arcade Dungeon")

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

        # Slash & Flash Animation states
        self._slashes = []
        self._flash_alpha = 0.0
        self._flash_color = (255, 255, 255)

        # Load animated player class spritesheets (128x128: 4 dirs x 4 frames)
        self._player_sheets = {}
        for cls in ("knight", "wizard", "rogue"):
            try:
                self._player_sheets[cls] = pygame.image.load(
                    f"assets/players/{cls}.png").convert_alpha()
            except Exception:
                pass

        # Load animated monster sprites (64x32: 2-frame idle wobble)
        self._monster_sprites = {}
        for mname in ("rat", "goblin", "orc", "troll", "wraith", "dread_knight",
                      "dragon", "mimic", "chest", "locked_chest"):
            try:
                self._monster_sprites[mname] = pygame.image.load(
                    f"assets/sprites/{mname}.png").convert_alpha()
            except Exception:
                pass

        # Load animated NPC sprites (128x32: 4-frame idle loop)
        self._npc_sprites = {}
        for nname in ("villager", "farmer", "druid", "merchant", "ghost_npc"):
            try:
                self._npc_sprites[nname] = pygame.image.load(
                    f"assets/npcs/{nname}.png").convert_alpha()
            except Exception:
                pass

        # Pre-build the CRT scanline + vignette overlay for the 8-bit arcade look
        self._crt_overlay = self._build_crt_overlay()


    def _init_fonts(self):
        # 80s DOS look: a fixed-width font rendered small (no anti-aliasing)
        # and upscaled into chunky pixel blocks. PT Mono / Andale Mono read
        # cleanest when blown up; fall back through other monospaces.
        mono = None
        for name in ["ptmono", "pt mono", "andalemono", "andale mono",
                     "couriernew", "courier new", "monaco", "menlo",
                     "consolas", "courier", "monospace"]:
            try:
                f = pygame.font.SysFont(name, 11)
                if f:
                    mono = name
                    break
            except Exception:
                pass

        # base_size x scale = effective height. Larger than before for
        # readability, with 2-3px blocks for that DOS-on-a-CRT feel.
        self._ui_font = RetroFont(mono, 10, scale=2)               # ~24px
        self._header_font = RetroFont(mono, 11, scale=2, bold=True)  # ~28px
        self._title_font = RetroFont(mono, 16, scale=3, bold=True)   # ~63px
        self._log_font = RetroFont(mono, 10, scale=2)              # ~24px


    def _build_crt_overlay(self):
        """Pre-render a CRT scanline + vignette overlay blitted over the whole
        frame each tick for an 80s arcade-cabinet feel."""
        overlay = pygame.Surface((TOTAL_WIDTH, TOTAL_HEIGHT), pygame.SRCALPHA)

        # Horizontal scanlines: a faint dark line every other row.
        line = (0, 0, 0, 38)
        for y in range(0, TOTAL_HEIGHT, 2):
            pygame.draw.line(overlay, line, (0, y), (TOTAL_WIDTH, y))

        # Soft vignette: darken the edges with concentric translucent rects.
        cx, cy = TOTAL_WIDTH / 2, TOTAL_HEIGHT / 2
        max_d = math.hypot(cx, cy)
        steps = 18
        for i in range(steps):
            t = i / steps
            inset = int(t * min(cx, cy))
            alpha = int(46 * (1.0 - t))
            if alpha <= 0:
                continue
            rect = pygame.Rect(inset, inset,
                               TOTAL_WIDTH - inset * 2, TOTAL_HEIGHT - inset * 2)
            pygame.draw.rect(overlay, (0, 0, 0, alpha), rect, width=2,
                             border_radius=0)
        return overlay

    def reset(self):
        # For backward compatibility with terminal redrawing triggers
        pass

    def trigger_shake(self, intensity=6.0):
        self._shake_intensity = intensity

    def add_slash(self, tile_x: int, tile_y: int, direction: str, color=(240, 240, 245)):
        self._slashes.append({
            "x": tile_x,
            "y": tile_y,
            "direction": direction,
            "color": color,
            "life": 1.0,
            "max_life": 1.0
        })

    def trigger_flash(self, alpha=160, color=(160, 220, 255)):
        self._flash_alpha = float(alpha)
        self._flash_color = color

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

        # 6. Update Screen Flash Decay
        if self._flash_alpha > 0:
            self._flash_alpha = max(0.0, self._flash_alpha - 15.0)

        # 7. Update Melee Slashes
        for s in list(self._slashes):
            s["life"] -= 0.12
            if s["life"] <= 0:
                self._slashes.remove(s)

    def render(self, level: DungeonLevel, player: Player, log: MessageLog, show_inventory=False, show_shop=None):
        # Tick calculations
        self.update_animations()

        # Background clearing
        self._screen.fill(ATARI_BG)

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

        # Render Melee Slashes
        self._draw_slashes(shake_x, shake_y)

        # Render Fireball Projectiles (Visuals)
        self._draw_projectiles(shake_x, shake_y)

        # Render Particles
        self._draw_particles(shake_x, shake_y)

        # Render Damage text overlay
        self._draw_damage_texts(shake_x, shake_y)

        # Render Screen Flash Overlay (only over map viewport)
        if self._flash_alpha > 0:
            flash_surf = pygame.Surface((MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT), pygame.SRCALPHA)
            flash_color_with_alpha = self._flash_color + (int(self._flash_alpha),)
            flash_surf.fill(flash_color_with_alpha)
            self._screen.blit(flash_surf, (0, 0))

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

        # CRT scanline + vignette overlay (drawn last, over everything)
        self._screen.blit(self._crt_overlay, (0, 0))

        pygame.display.flip()

    def _draw_map(self, level: DungeonLevel, shake_x: int, shake_y: int):
        w = min(MAP_WIDTH, level.width)
        h = min(MAP_HEIGHT, level.height)
        is_overworld = getattr(level, "is_overworld", False)
        
        for x in range(w):
            for y in range(h):
                t = level.tiles[x][y]
                if not t.explored:
                    continue

                rect = pygame.Rect(x * TILE_SIZE + shake_x, y * TILE_SIZE + shake_y, TILE_SIZE, TILE_SIZE)

                # Fetch basic tile color definitions
                visible = t.visible

                if is_overworld:
                    # Determine overworld quadrant
                    in_town = (x < 15 and y < 9)
                    in_farm = (x >= 15 and y < 9)
                    in_cemetery = (x < 15 and y >= 9)
                    in_field = (x >= 15 and y >= 9)
                    
                    if t.type == TileType.WALL:
                        if in_town:
                            color = (120, 80, 50) if visible else (70, 45, 30)
                            self._draw_wooden_wall(rect, color)
                        elif in_farm:
                            color = (95, 70, 45) if visible else (55, 40, 25)
                            self._draw_fence(rect, color)
                        elif in_cemetery:
                            color = (80, 80, 80) if visible else (45, 45, 45)
                            self._draw_stone_wall(rect, color)
                        else:
                            color = (34, 120, 40) if visible else (20, 70, 25)
                            self._draw_hedge(rect, color)
                            
                    elif t.type == TileType.FLOOR:
                        if in_town:
                            color = (55, 52, 50) if visible else (32, 30, 28)
                            self._draw_cobblestone(rect, color, visible)
                        elif in_farm:
                            color = (65, 48, 32) if visible else (38, 28, 20)
                            self._draw_tilled_soil(rect, color, visible)
                        elif in_cemetery:
                            color = (40, 45, 40) if visible else (24, 28, 24)
                            self._draw_dark_grass(rect, color, visible)
                        else:
                            color = (34, 85, 34) if visible else (20, 50, 20)
                            self._draw_grass(rect, color, visible)
                            
                    elif t.type == TileType.STAIRS_DOWN:
                        if in_farm:
                            self._draw_cellar_hatch(rect, visible)
                        elif in_cemetery:
                            self._draw_crypt_entrance(rect, visible)
                        else:
                            self._draw_cave_entrance(rect, visible)
                else:
                    if t.type == TileType.WALL:
                        color = (44, 86, 154) if visible else (24, 42, 78)
                        self._draw_brick_wall(rect, color)
                    elif t.type == TileType.FLOOR:
                        color = (34, 24, 44) if visible else (18, 14, 26)
                        self._draw_floor(rect, color, visible)
                    elif t.type == TileType.STAIRS_DOWN:
                        color = (34, 24, 44) if visible else (18, 14, 26)
                        self._draw_floor(rect, color, visible)
                        stairs_color = (250, 198, 64) if visible else (138, 96, 30)
                        self._draw_stairs_down(rect, stairs_color)
                    elif t.type == TileType.STAIRS_UP:
                        color = (34, 24, 44) if visible else (18, 14, 26)
                        self._draw_floor(rect, color, visible)
                        stairs_color = (174, 224, 255) if visible else (92, 128, 168)
                        self._draw_stairs_up(rect, stairs_color)
                    elif t.type == TileType.FOUNTAIN:
                        color = (34, 24, 44) if visible else (18, 14, 26)
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

    def _draw_wooden_wall(self, rect: pygame.Rect, color: tuple[int, int, int]):
        pygame.draw.rect(self._screen, color, rect)
        plank_h = rect.height // 3
        for i in range(1, 3):
            y = rect.top + i * plank_h
            pygame.draw.line(self._screen, (40, 25, 15), (rect.left, y), (rect.right, y), 2)
        hl = tuple(min(255, c + 30) for c in color)
        pygame.draw.line(self._screen, hl, rect.topleft, rect.topright)

    def _draw_fence(self, rect: pygame.Rect, color: tuple[int, int, int]):
        pygame.draw.rect(self._screen, (34, 85, 34), rect)
        pygame.draw.rect(self._screen, color, (rect.left, rect.centery - 3, rect.width, 4))
        pygame.draw.rect(self._screen, color, (rect.left + 4, rect.top, 4, rect.height))
        pygame.draw.rect(self._screen, color, (rect.right - 8, rect.top, 4, rect.height))

    def _draw_stone_wall(self, rect: pygame.Rect, color: tuple[int, int, int]):
        pygame.draw.rect(self._screen, color, rect)
        hl = tuple(min(255, c + 35) for c in color)
        pygame.draw.line(self._screen, hl, rect.topleft, rect.topright)
        pygame.draw.line(self._screen, hl, rect.topleft, rect.bottomleft)
        pygame.draw.line(self._screen, (30, 30, 30), (rect.left, rect.centery), (rect.right, rect.centery))
        pygame.draw.line(self._screen, (30, 30, 30), (rect.centerx, rect.top), (rect.centerx, rect.centery))
        pygame.draw.line(self._screen, (30, 30, 30), (rect.left + 6, rect.centery), (rect.left + 6, rect.bottom))
        pygame.draw.line(self._screen, (30, 30, 30), (rect.right - 6, rect.centery), (rect.right - 6, rect.bottom))

    def _draw_hedge(self, rect: pygame.Rect, color: tuple[int, int, int]):
        pygame.draw.rect(self._screen, (34, 85, 34), rect)
        pygame.draw.circle(self._screen, color, rect.center, 14)
        hl = tuple(min(255, c + 40) for c in color)
        pygame.draw.circle(self._screen, hl, (rect.centerx - 3, rect.centery - 3), 6)

    def _draw_cobblestone(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        pygame.draw.rect(self._screen, color, rect)
        stone_color = (90, 85, 80) if visible else (50, 48, 45)
        pygame.draw.circle(self._screen, stone_color, (rect.left + 8, rect.top + 8), 4)
        pygame.draw.circle(self._screen, stone_color, (rect.right - 8, rect.top + 10), 3)
        pygame.draw.circle(self._screen, stone_color, (rect.left + 10, rect.bottom - 8), 3)
        pygame.draw.circle(self._screen, stone_color, (rect.right - 10, rect.bottom - 10), 4)

    def _draw_tilled_soil(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        pygame.draw.rect(self._screen, color, rect)
        line_color = (50, 35, 20) if visible else (30, 20, 12)
        pygame.draw.line(self._screen, line_color, (rect.left, rect.top + 8), (rect.right, rect.top + 8), 2)
        pygame.draw.line(self._screen, line_color, (rect.left, rect.bottom - 8), (rect.right, rect.bottom - 8), 2)
        if visible and (rect.x + rect.y) % 3 == 0:
            pygame.draw.circle(self._screen, (34, 180, 34), (rect.centerx, rect.top + 6), 2)
            pygame.draw.circle(self._screen, (34, 180, 34), (rect.centerx, rect.bottom - 10), 2)

    def _draw_dark_grass(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        pygame.draw.rect(self._screen, color, rect)
        if (rect.x * 7 + rect.y * 13) % 5 == 0:
            dot_color = (60, 65, 60) if visible else (35, 38, 35)
            pygame.draw.rect(self._screen, dot_color, (rect.centerx - 2, rect.centery - 4, 4, 6), border_radius=1)

    def _draw_grass(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        pygame.draw.rect(self._screen, color, rect)
        if visible and (rect.x + rect.y * 3) % 4 == 0:
            tuft_color = (60, 130, 60)
            pygame.draw.line(self._screen, tuft_color, (rect.centerx, rect.centery + 3), (rect.centerx - 2, rect.centery - 3), 1)
            pygame.draw.line(self._screen, tuft_color, (rect.centerx, rect.centery + 3), (rect.centerx + 2, rect.centery - 2), 1)

    def _draw_cellar_hatch(self, rect: pygame.Rect, visible: bool):
        door_color = (110, 65, 25) if visible else (55, 32, 12)
        pygame.draw.rect(self._screen, door_color, rect, border_radius=1)
        pygame.draw.line(self._screen, (40, 25, 10), (rect.centerx, rect.top), (rect.centerx, rect.bottom), 2)
        hinge_color = (120, 120, 125) if visible else (60, 60, 62)
        pygame.draw.rect(self._screen, hinge_color, (rect.left + 2, rect.top + 4, 4, 2))
        pygame.draw.rect(self._screen, hinge_color, (rect.right - 6, rect.top + 4, 4, 2))
        pygame.draw.rect(self._screen, hinge_color, (rect.left + 2, rect.bottom - 6, 4, 2))
        pygame.draw.rect(self._screen, hinge_color, (rect.right - 6, rect.bottom - 6, 4, 2))

    def _draw_crypt_entrance(self, rect: pygame.Rect, visible: bool):
        pygame.draw.rect(self._screen, (30, 30, 30), rect)
        stone_color = (100, 100, 105) if visible else (50, 50, 52)
        pygame.draw.arc(self._screen, stone_color, (rect.left + 4, rect.top + 2, rect.width - 8, rect.height - 4), 0, math.pi, width=4)
        step_color = (60, 60, 65) if visible else (30, 30, 32)
        pygame.draw.rect(self._screen, step_color, (rect.left + 8, rect.centery, rect.width - 16, 4))
        pygame.draw.rect(self._screen, step_color, (rect.left + 10, rect.centery + 4, rect.width - 20, 4))

    def _draw_cave_entrance(self, rect: pygame.Rect, visible: bool):
        pygame.draw.rect(self._screen, (34, 85, 34), rect)
        pygame.draw.ellipse(self._screen, (10, 10, 12), (rect.left + 3, rect.top + 3, rect.width - 6, rect.height - 6))
        rock_color = (120, 110, 100) if visible else (60, 55, 50)
        pygame.draw.ellipse(self._screen, rock_color, (rect.left + 3, rect.top + 3, rect.width - 6, rect.height - 6), width=2)

    def _draw_brick_wall(self, rect: pygame.Rect, color: tuple[int, int, int]):
        # Chunky 8-bit wall blocks with dithering and hard highlights.
        pygame.draw.rect(self._screen, color, rect)
        hi = tuple(min(255, c + 40) for c in color)
        lo = tuple(max(0, c - 36) for c in color)
        pygame.draw.rect(self._screen, hi, (rect.left, rect.top, rect.width, 3))
        pygame.draw.rect(self._screen, hi, (rect.left, rect.top, 3, rect.height))
        pygame.draw.rect(self._screen, lo, (rect.left, rect.bottom - 3, rect.width, 3))
        pygame.draw.rect(self._screen, lo, (rect.right - 3, rect.top, 3, rect.height))

        mortar = tuple(max(0, c - 20) for c in color)
        for y in range(rect.top + 8, rect.bottom, 8):
            pygame.draw.line(self._screen, mortar, (rect.left + 2, y), (rect.right - 2, y), 1)
        for x in range(rect.left + 6, rect.right, 12):
            pygame.draw.line(self._screen, mortar, (x, rect.top + 2), (x, rect.top + 12), 1)
            pygame.draw.line(self._screen, mortar, (x + 6, rect.top + 14), (x + 6, rect.bottom - 2), 1)

    def _draw_floor(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        pygame.draw.rect(self._screen, color, rect)

        # Ordered dither to mimic low-color arcade tile shading.
        dot_color = (66, 52, 90) if visible else (34, 30, 48)
        for dx in range(2, TILE_SIZE, 4):
            for dy in range(2, TILE_SIZE, 4):
                if ((rect.x + dx) // 2 + (rect.y + dy) // 2) % 2 == 0:
                    self._screen.fill(dot_color, (rect.x + dx, rect.y + dy, 2, 2))

        if visible:
            pulse = 1 if (self._frame_count // 24) % 2 == 0 else 0
            glow = (96 + 12 * pulse, 66 + 8 * pulse, 130 + 16 * pulse)
            pygame.draw.rect(self._screen, glow, (rect.left + 3, rect.top + 3, 2, 2))

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
                self._draw_weapon(rect, color, ie.item.name)
            elif ie.item.kind.value == "wand":
                self._draw_wand(rect, color)
            elif ie.item.kind.value == "coin":
                self._draw_coin(rect)
            elif ie.item.kind.value == "key":
                self._draw_key(rect)
            elif ie.item.kind.value == "arrow":
                self._draw_arrows_item(rect)
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

    def _draw_weapon(self, rect: pygame.Rect, color: tuple[int, int, int], name: str = ""):
        if name == "bow":
            self._draw_bow(rect, color)
            return

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

    def _draw_bow(self, rect: pygame.Rect, color: tuple[int, int, int]):
        # Curved wooden bow curve points bent toward top-right
        start_pt = (rect.left + 8, rect.top + 8)
        end_pt = (rect.right - 8, rect.bottom - 8)
        control_pt = (rect.right - 6, rect.top + 6)
        
        points = []
        for i in range(11):
            t = i / 10
            x = (1-t)**2 * start_pt[0] + 2*(1-t)*t * control_pt[0] + t**2 * end_pt[0]
            y = (1-t)**2 * start_pt[1] + 2*(1-t)*t * control_pt[1] + t**2 * end_pt[1]
            points.append((int(x), int(y)))
        pygame.draw.lines(self._screen, (139, 90, 43), False, points, 3)
        
        # Glow highlights if blessed
        if color != color_rgb(Color.CYAN):
            pygame.draw.lines(self._screen, color, False, points, 1)

        # Bow string (thin light grey)
        pygame.draw.line(self._screen, (220, 220, 225), start_pt, end_pt, 1)

    def _draw_arrows_item(self, rect: pygame.Rect):
        # Draw 2 crossed arrows on the floor
        # Shaft 1
        pygame.draw.line(self._screen, (139, 90, 43), (rect.left + 8, rect.bottom - 8), (rect.right - 8, rect.top + 8), 2)
        # Shaft 2
        pygame.draw.line(self._screen, (139, 90, 43), (rect.left + 8, rect.top + 8), (rect.right - 8, rect.bottom - 8), 2)
        # Fletchings (little white flight circles)
        pygame.draw.circle(self._screen, (240, 240, 245), (rect.left + 8, rect.bottom - 8), 2)
        pygame.draw.circle(self._screen, (240, 240, 245), (rect.left + 8, rect.top + 8), 2)
        # Arrow heads
        pygame.draw.polygon(self._screen, (200, 200, 210), [(rect.right - 8, rect.top + 8), (rect.right - 12, rect.top + 6), (rect.right - 6, rect.top + 12)])
        pygame.draw.polygon(self._screen, (200, 200, 210), [(rect.right - 8, rect.bottom - 8), (rect.right - 12, rect.bottom - 6), (rect.right - 6, rect.bottom - 12)])

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
            sprite_name = getattr(m, "npc_type", m.name) if getattr(m, "is_npc", False) else m.name
            self._draw_monster_sprite(rect, sprite_name, color_rgb(m.color))

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
        # Animated pixel-art NPC if we generated one (4-frame idle loop).
        npc_sheet = self._npc_sprites.get(name.replace(" ", "_"))
        if npc_sheet is not None:
            frame = (self._frame_count // 11) % 4
            src = pygame.Rect(frame * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
            self._screen.blit(npc_sheet, rect.topleft, src)
            return

        # Animated pixel-art sprite if we generated one for this monster
        # (4-frame idle loop with per-monster motion + flourish).
        sheet = self._monster_sprites.get(name.replace(" ", "_"))
        if sheet is not None:
            frame = (self._frame_count // 12) % 4
            src = pygame.Rect(frame * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE)
            self._screen.blit(sheet, rect.topleft, src)
            # Live drifting nostril smoke for the dragon (sprite can't drift).
            if name == "dragon" and self._frame_count % 12 == 0:
                self._particles.append({
                    "x": rect.centerx + 8, "y": rect.centery + 6,
                    "vx": random.uniform(0.1, 0.4), "vy": random.uniform(-0.2, 0.2),
                    "color": (250, 100, 20) if random.random() > 0.5 else (120, 120, 120),
                    "size": random.uniform(1.5, 3),
                    "life": random.uniform(0.2, 0.4), "max_life": 1.0,
                })
            return

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
            # 1. Cloak and robes
            pygame.draw.rect(self._screen, (90, 60, 35), (rect.centerx - 6, rect.top + 12, 12, 15), border_radius=2)
            pygame.draw.rect(self._screen, (70, 45, 25), (rect.centerx - 5, rect.top + 25, 3, 4)) # Left boot
            pygame.draw.rect(self._screen, (70, 45, 25), (rect.centerx + 2, rect.top + 25, 3, 4)) # Right boot
            # 2. Cowl / Hood
            pygame.draw.circle(self._screen, (110, 75, 45), (rect.centerx, rect.top + 7), 8)
            pygame.draw.circle(self._screen, (25, 20, 15), (rect.centerx, rect.top + 7), 5.5)
            pygame.draw.circle(self._screen, (255, 215, 0), (rect.centerx - 2, rect.top + 6), 1) # Glowing eyes
            pygame.draw.circle(self._screen, (255, 215, 0), (rect.centerx + 2, rect.top + 6), 1)
            pygame.draw.circle(self._screen, (255, 215, 0), (rect.centerx, rect.top + 13), 2) # clasp
            # 3. Arms holding a small gold coin
            pygame.draw.line(self._screen, (90, 60, 35), (rect.centerx - 6, rect.top + 14), (rect.centerx - 8, rect.top + 19), 2)
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx - 8, rect.top + 19), 2)
            pygame.draw.circle(self._screen, (215, 175, 20), (rect.centerx - 9, rect.top + 20), 2)
        elif name == "villager":
            # 1. Legs & Shoes
            pygame.draw.rect(self._screen, (75, 75, 80), (rect.centerx - 4, rect.top + 23, 3, 6)) # Left leg
            pygame.draw.rect(self._screen, (75, 75, 80), (rect.centerx + 1, rect.top + 23, 3, 6)) # Right leg
            pygame.draw.rect(self._screen, (80, 50, 30), (rect.centerx - 5, rect.top + 28, 4, 3), border_radius=1) # Left shoe
            pygame.draw.rect(self._screen, (80, 50, 30), (rect.centerx + 1, rect.top + 28, 4, 3), border_radius=1) # Right shoe
            # 2. Body / Tunic
            pygame.draw.rect(self._screen, (50, 100, 220), (rect.centerx - 6, rect.top + 12, 12, 12), border_radius=2)
            # Brown belt
            pygame.draw.rect(self._screen, (100, 65, 35), (rect.centerx - 6, rect.top + 18, 12, 2))
            # 3. Head & Hair
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx, rect.top + 8), 5)
            # Brown hair on top/sides
            pygame.draw.rect(self._screen, (90, 50, 20), (rect.centerx - 6, rect.top + 3, 12, 3), border_radius=1)
            pygame.draw.rect(self._screen, (90, 50, 20), (rect.centerx - 6, rect.top + 3, 2, 6))
            pygame.draw.rect(self._screen, (90, 50, 20), (rect.centerx + 4, rect.top + 3, 2, 6))
            # 4. Face features
            pygame.draw.circle(self._screen, (30, 30, 30), (rect.centerx - 2, rect.top + 7), 1) # Left eye
            pygame.draw.circle(self._screen, (30, 30, 30), (rect.centerx + 2, rect.top + 7), 1) # Right eye
            pygame.draw.line(self._screen, (200, 80, 80), (rect.centerx - 1, rect.top + 10), (rect.centerx + 1, rect.top + 10), 1) # Smile
            # 5. Arms & Hands
            pygame.draw.line(self._screen, (50, 100, 220), (rect.centerx - 6, rect.top + 14), (rect.centerx - 8, rect.top + 20), 2)
            pygame.draw.line(self._screen, (50, 100, 220), (rect.centerx + 6, rect.top + 14), (rect.centerx + 8, rect.top + 20), 2)
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx - 8, rect.top + 20), 2)
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx + 8, rect.top + 20), 2)
        elif name == "farmer":
            # 1. Legs & Workboots
            pygame.draw.rect(self._screen, (40, 85, 170), (rect.centerx - 4, rect.top + 23, 3, 6)) # Left pant leg
            pygame.draw.rect(self._screen, (40, 85, 170), (rect.centerx + 1, rect.top + 23, 3, 6)) # Right pant leg
            pygame.draw.rect(self._screen, (90, 60, 30), (rect.centerx - 5, rect.top + 28, 4, 3), border_radius=1) # Left boot
            pygame.draw.rect(self._screen, (90, 60, 30), (rect.centerx + 1, rect.top + 28, 4, 3), border_radius=1) # Right boot
            # 2. Torso (Red Shirt & Blue Overalls)
            pygame.draw.rect(self._screen, (200, 50, 50), (rect.centerx - 6, rect.top + 12, 12, 12), border_radius=1) # Red shirt
            # Draw blue overalls over shirt
            pygame.draw.rect(self._screen, (40, 85, 170), (rect.centerx - 5, rect.top + 16, 10, 8), border_radius=1)
            # Suspender straps
            pygame.draw.line(self._screen, (40, 85, 170), (rect.centerx - 4, rect.top + 12), (rect.centerx - 4, rect.top + 16), 2)
            pygame.draw.line(self._screen, (40, 85, 170), (rect.centerx + 3, rect.top + 12), (rect.centerx + 3, rect.top + 16), 2)
            # 3. Head & Straw Hat
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx, rect.top + 8), 5) # Head
            # Face details
            pygame.draw.circle(self._screen, (30, 30, 30), (rect.centerx - 2, rect.top + 7), 1)
            pygame.draw.circle(self._screen, (30, 30, 30), (rect.centerx + 2, rect.top + 7), 1)
            # Wide straw hat brim
            pygame.draw.ellipse(self._screen, (220, 200, 80), (rect.centerx - 10, rect.top + 1, 20, 4))
            pygame.draw.rect(self._screen, (220, 200, 80), (rect.centerx - 5, rect.top - 2, 10, 4), border_radius=1)
            # 4. Arms holding wheat
            pygame.draw.line(self._screen, (200, 50, 50), (rect.centerx - 6, rect.top + 14), (rect.centerx - 9, rect.top + 19), 2)
            pygame.draw.line(self._screen, (200, 50, 50), (rect.centerx + 6, rect.top + 14), (rect.centerx + 8, rect.top + 19), 2)
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx - 9, rect.top + 19), 2) # Left hand
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx + 8, rect.top + 19), 2) # Right hand
            # Golden wheat stalk in hand
            pygame.draw.line(self._screen, (100, 160, 50), (rect.centerx - 9, rect.top + 24), (rect.centerx - 11, rect.top + 12), 1) # stem
            pygame.draw.ellipse(self._screen, (230, 200, 50), (rect.centerx - 13, rect.top + 9, 3, 5)) # seed head
        elif name == "ghost_npc":
            # Friendly ghost sprite (translucent blue)
            ghost_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(ghost_surf, (150, 220, 255, 150), (16, 12), 7)
            pygame.draw.polygon(ghost_surf, (150, 220, 255, 150), [(9, 12), (23, 12), (16, 26)])
            pygame.draw.circle(ghost_surf, (255, 255, 255, 200), (13, 11), 2)
            pygame.draw.circle(ghost_surf, (255, 255, 255, 200), (19, 11), 2)
            self._screen.blit(ghost_surf, rect.topleft)
        elif name == "druid":
            # 1. Robe (Green and Gold trim)
            pygame.draw.rect(self._screen, (30, 120, 30), (rect.centerx - 6, rect.top + 12, 12, 16), border_radius=2)
            pygame.draw.rect(self._screen, (235, 185, 30), (rect.centerx - 6, rect.top + 26, 12, 2))
            # 2. Head & hood
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx, rect.top + 8), 5) # Face
            pygame.draw.circle(self._screen, (30, 100, 30), (rect.centerx, rect.top + 7), 7, width=2)
            # 3. Flowing white beard
            pygame.draw.polygon(self._screen, (245, 245, 245), [
                (rect.centerx - 3, rect.top + 10),
                (rect.centerx + 3, rect.top + 10),
                (rect.centerx, rect.top + 19)
            ])
            # Glowing emerald eyes
            pygame.draw.circle(self._screen, (50, 240, 50), (rect.centerx - 2, rect.top + 7), 1)
            pygame.draw.circle(self._screen, (50, 240, 50), (rect.centerx + 2, rect.top + 7), 1)
            # 4. Arms & staff
            pygame.draw.line(self._screen, (30, 120, 30), (rect.centerx + 6, rect.top + 14), (rect.centerx + 8, rect.top + 18), 2)
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx + 8, rect.top + 18), 2) # Right hand
            # Wooden staff
            pygame.draw.line(self._screen, (120, 75, 35), (rect.centerx + 10, rect.bottom - 4), (rect.centerx + 10, rect.top + 2), 3)
            pygame.draw.circle(self._screen, (0, 200, 255), (rect.centerx + 10, rect.top + 2), 3)
            pygame.draw.circle(self._screen, (255, 255, 255), (rect.centerx + 10, rect.top + 2), 1)
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
        elif name == "dragon":
            # 1. Main body/head shape: large ellipse
            pygame.draw.ellipse(self._screen, color, pygame.Rect(rect.centerx - 12, rect.centery - 10, 24, 20))
            # 2. Snout/jaw pointing forward
            pygame.draw.polygon(self._screen, color, [
                (rect.centerx - 8, rect.centery + 2),
                (rect.centerx + 12, rect.centery + 8),
                (rect.centerx - 4, rect.centery + 10)
            ])
            # 3. Horns on the back of the head
            pygame.draw.polygon(self._screen, (160, 40, 40), [
                (rect.centerx - 8, rect.centery - 8),
                (rect.centerx - 14, rect.centery - 15),
                (rect.centerx - 2, rect.centery - 10)
            ])
            pygame.draw.polygon(self._screen, (160, 40, 40), [
                (rect.centerx - 4, rect.centery - 9),
                (rect.centerx - 8, rect.centery - 16),
                (rect.centerx + 2, rect.centery - 10)
            ])
            # 4. Glowing yellow eyes
            pygame.draw.circle(self._screen, (255, 230, 0), (rect.centerx + 2, rect.centery - 2), 2)
            # 5. Nostril smoke/fire particles (subtle animation!)
            if self._frame_count % 12 == 0:
                self._particles.append({
                    "x": rect.centerx + 8,
                    "y": rect.centery + 6,
                    "vx": random.uniform(0.1, 0.4),
                    "vy": random.uniform(-0.2, 0.2),
                    "color": (250, 100, 20) if random.random() > 0.5 else (120, 120, 120),
                    "size": random.uniform(1.5, 3),
                    "life": random.uniform(0.2, 0.4),
                    "max_life": 1.0
                })
        else:
            # Threat marker dot
            pygame.draw.circle(self._screen, color, rect.center, 8)

    def _draw_player_sprite(self, rect: pygame.Rect, color: tuple[int, int, int], enchanted: bool, player: Player = None):
        # Ground shadow anchors the sprite while it bobs.
        shadow_rect = pygame.Rect(rect.left + 5, rect.bottom - 8, 22, 7)
        pygame.draw.ellipse(self._screen, (8, 8, 12), shadow_rect)

        # Glow ring if enchanted
        if enchanted:
            pygame.draw.circle(self._screen, (246, 206, 66), rect.center, 13, 2)

        char_class = "Wizard"
        if player and hasattr(player, "char_class"):
            char_class = player.char_class

        # Draw animated pixel-art spritesheet for any class we have art for.
        sheet = self._player_sheets.get(char_class.lower())
        if sheet and player:
            dir_rows = {"DOWN": 0, "UP": 1, "LEFT": 2, "RIGHT": 3}
            row = dir_rows.get(player.facing, 0)

            # Is the player visually mid-step?
            is_moving = False
            if player in self._entity_positions:
                vx, vy = self._entity_positions[player]
                tx, ty = player.x * TILE_SIZE, player.y * TILE_SIZE
                is_moving = (math.hypot(tx - vx, ty - vy) > 0.5)

            attacking = player in self._bumps
            if is_moving or attacking:
                # Full walk cycle while moving / lunging.
                frame_idx = (self._frame_count // 5) % 4
                bob = int(math.sin(self._frame_count * 0.5) * 1.5)
                if self._frame_count % 7 == 0:
                    self._particles.append({
                        "x": rect.centerx + random.uniform(-5, 5),
                        "y": rect.bottom - 5,
                        "vx": random.uniform(-0.25, 0.25),
                        "vy": random.uniform(-0.55, -0.2),
                        "color": (120, 120, 138),
                        "size": random.uniform(1.0, 2.0),
                        "life": random.uniform(0.18, 0.32),
                        "max_life": 1.0,
                    })
            else:
                # Idle animation cycles through all poses with a slow breathing bob.
                frame_idx = (self._frame_count // 14) % 4
                bob = int(math.sin(self._frame_count * 0.17) * 2)

            src_rect = pygame.Rect(frame_idx * 32, row * 32, 32, 32)
            self._screen.blit(sheet, (rect.left, rect.top + bob), src_rect)
            return

        # Fallback vector sprites for classes
        if char_class == "Knight":
            # 1. Legs and steel boots
            pygame.draw.rect(self._screen, (110, 110, 115), (rect.centerx - 4, rect.centery + 8, 3, 5)) # Left leg
            pygame.draw.rect(self._screen, (110, 110, 115), (rect.centerx + 1, rect.centery + 8, 3, 5)) # Right leg
            pygame.draw.rect(self._screen, (50, 50, 50), (rect.centerx - 5, rect.centery + 12, 4, 3), border_radius=1) # Left boot
            pygame.draw.rect(self._screen, (50, 50, 50), (rect.centerx + 1, rect.centery + 12, 4, 3), border_radius=1) # Right boot
            # 2. Chestplate
            pygame.draw.rect(self._screen, (130, 130, 140), (rect.centerx - 7, rect.centery - 2, 14, 11), border_radius=2)
            # 3. Helmet & plume
            pygame.draw.circle(self._screen, (170, 170, 180), (rect.centerx, rect.centery - 6), 6)
            pygame.draw.rect(self._screen, (35, 35, 40), (rect.centerx - 4, rect.centery - 7, 8, 2)) # Visor slot
            pygame.draw.circle(self._screen, (220, 40, 40), (rect.centerx, rect.top + 5), 2) # Red plume
            # 4. Shield (on left arm)
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
            # 5. Sword in right arm
            pygame.draw.line(self._screen, (130, 130, 140), (rect.centerx + 6, rect.centery + 2), (rect.centerx + 9, rect.centery + 5), 2) # arm
            pygame.draw.line(self._screen, (210, 215, 220), (rect.centerx + 9, rect.centery + 5), (rect.centerx + 13, rect.centery - 4), 2) # Blade
            pygame.draw.line(self._screen, (245, 205, 35), (rect.centerx + 7, rect.centery + 6), (rect.centerx + 11, rect.centery + 3), 2) # Guard
        elif char_class == "Rogue":
            # Green Rogue drawing
            # 1. Legs and boots
            pygame.draw.rect(self._screen, (40, 45, 42), (rect.centerx - 4, rect.centery + 8, 3, 5)) # Left leg
            pygame.draw.rect(self._screen, (40, 45, 42), (rect.centerx + 1, rect.centery + 8, 3, 5)) # Right leg
            pygame.draw.rect(self._screen, (60, 45, 30), (rect.centerx - 5, rect.centery + 12, 4, 3), border_radius=1) # Left shoe
            pygame.draw.rect(self._screen, (60, 45, 30), (rect.centerx + 1, rect.centery + 12, 4, 3), border_radius=1) # Right shoe
            # 2. Cloak forest green
            pygame.draw.circle(self._screen, (34, 110, 56), rect.center, 8)
            # 3. Dark cowl/hood
            pygame.draw.circle(self._screen, (45, 55, 50), (rect.centerx, rect.centery - 4), 6)
            # Shadowy mask inside cowl
            pygame.draw.circle(self._screen, (20, 22, 20), (rect.centerx, rect.centery - 4), 4)
            # Glinting eyes
            pygame.draw.circle(self._screen, (180, 220, 255), (rect.centerx - 1, rect.centery - 5), 1)
            pygame.draw.circle(self._screen, (180, 220, 255), (rect.centerx + 1, rect.centery - 5), 1)
            # 4. Steel dagger in hand
            pygame.draw.line(self._screen, (200, 200, 205), (rect.centerx + 5, rect.centery), (rect.centerx + 10, rect.centery - 5), 2)
            pygame.draw.line(self._screen, (120, 80, 40), (rect.centerx + 4, rect.centery + 1), (rect.centerx + 6, rect.centery - 1), 2)
        else:
            # Wizard Cloak (deep purple)
            # 1. Robe down to legs
            pygame.draw.rect(self._screen, (100, 45, 175), (rect.centerx - 6, rect.centery - 2, 12, 14), border_radius=2)
            pygame.draw.rect(self._screen, (90, 60, 35), (rect.centerx - 5, rect.centery + 11, 4, 3), border_radius=1) # Left shoe
            pygame.draw.rect(self._screen, (90, 60, 35), (rect.centerx + 1, rect.centery + 11, 4, 3), border_radius=1) # Right shoe
            pygame.draw.circle(self._screen, (245, 205, 35), (rect.centerx, rect.centery + 2), 2) # Gold emblem
            # 2. Face peeking out from under hat
            pygame.draw.circle(self._screen, (240, 200, 160), (rect.centerx, rect.centery - 5), 5)
            # Glowing wizard eyes (white/light-blue)
            pygame.draw.circle(self._screen, (150, 220, 255), (rect.centerx - 1.5, rect.centery - 5), 1)
            pygame.draw.circle(self._screen, (150, 220, 255), (rect.centerx + 1.5, rect.centery - 5), 1)
            # 3. Conical Wizard Hat
            hat_points = [
                (rect.centerx, rect.top + 3),
                (rect.centerx - 8, rect.centery - 4),
                (rect.centerx + 8, rect.centery - 4)
            ]
            pygame.draw.polygon(self._screen, (70, 30, 130), hat_points)
            pygame.draw.ellipse(self._screen, (245, 205, 35), (rect.centerx - 9, rect.centery - 6, 18, 4)) # Gold brim
            # 4. Staff in hand
            pygame.draw.line(self._screen, (120, 75, 35), (rect.centerx - 8, rect.centery + 11), (rect.centerx - 8, rect.centery - 4), 2)
            pygame.draw.circle(self._screen, (0, 200, 255), (rect.centerx - 8, rect.centery - 4), 3)

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
            elif ptype == "arrow" or ptype == "flame_arrow":
                # Draw a vector arrow pointing in direction of travel
                dx = path[-1][0] - path[0][0]
                dy = path[-1][1] - path[0][1]
                angle = math.atan2(dy, dx)
                
                # Shaft length
                arrow_len = 16
                bx = px - math.cos(angle) * (arrow_len / 2)
                by = py - math.sin(angle) * (arrow_len / 2)
                fx = px + math.cos(angle) * (arrow_len / 2)
                fy = py + math.sin(angle) * (arrow_len / 2)
                
                # Brown wooden shaft
                pygame.draw.line(self._screen, (139, 90, 43), (int(bx), int(by)), (int(fx), int(fy)), 2)
                # Steel/Flame triangular arrowhead
                tip_len = 4
                tx1 = fx - math.cos(angle + math.pi/6) * tip_len
                ty1 = fy - math.sin(angle + math.pi/6) * tip_len
                tx2 = fx - math.cos(angle - math.pi/6) * tip_len
                ty2 = fy - math.sin(angle - math.pi/6) * tip_len
                tip_color = (255, 69, 0) if ptype == "flame_arrow" else (200, 200, 210)
                pygame.draw.polygon(self._screen, tip_color, [(int(fx), int(fy)), (int(tx1), int(ty1)), (int(tx2), int(ty2))])
                # Feathers flight fletching
                f_angle1 = angle + math.pi * 5/6
                f_angle2 = angle - math.pi * 5/6
                f_len = 4
                fx1 = bx + math.cos(f_angle1) * f_len
                fy1 = by + math.sin(f_angle1) * f_len
                fx2 = bx + math.cos(f_angle2) * f_len
                fy2 = by + math.sin(f_angle2) * f_len
                f_color = (255, 140, 0) if ptype == "flame_arrow" else (240, 240, 245)
                pygame.draw.line(self._screen, f_color, (int(bx), int(by)), (int(fx1), int(fy1)), 2)
                pygame.draw.line(self._screen, f_color, (int(bx), int(by)), (int(fx2), int(fy2)), 2)
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

    def _draw_slashes(self, shake_x: int, shake_y: int):
        for s in self._slashes:
            tx, ty = s["x"], s["y"]
            direction = s["direction"]
            color = s["color"]
            life = s["life"]
            
            # Reconstruct player position to center the arc on the player
            px, py = tx, ty
            if direction == "RIGHT":
                px = tx - 1
            elif direction == "LEFT":
                px = tx + 1
            elif direction == "UP":
                py = ty + 1
            elif direction == "DOWN":
                py = ty - 1
                
            # Center of the player tile in pixels
            px_center = int((px + 0.5) * TILE_SIZE)
            py_center = int((py + 0.5) * TILE_SIZE)
            
            # The radius sweeps near the target tile
            R = int(TILE_SIZE * 0.95)
            
            # Use a 120x120 temporary surface centered around the player's position
            temp_surf = pygame.Surface((120, 120), pygame.SRCALPHA)
            cx, cy = 60, 60
            
            # Determine center angle based on direction (0 is right, pi/2 is up, pi is left, 3*pi/2 is down)
            if direction == "RIGHT":
                center_angle = 0.0
            elif direction == "UP":
                center_angle = math.pi / 2.0
            elif direction == "LEFT":
                center_angle = math.pi
            elif direction == "DOWN":
                center_angle = 3.0 * math.pi / 2.0
            else:
                center_angle = 0.0
                
            # Sweep angle is 100 degrees total (50 degrees each side)
            half_sweep = math.radians(50)
            num_segments = 12
            
            points = []
            for i in range(num_segments + 1):
                angle = center_angle - half_sweep + (2.0 * half_sweep * i / num_segments)
                # In Pygame, y increases downwards, so math positive y is screen negative y
                x_p = int(cx + R * math.cos(angle))
                y_p = int(cy - R * math.sin(angle))
                points.append((x_p, y_p))
                
            if len(points) > 1:
                # 1. Broad outer glow (low alpha, wide)
                glow_alpha_1 = int(70 * life)
                glow_color_1 = color + (glow_alpha_1,)
                pygame.draw.lines(temp_surf, glow_color_1, False, points, width=6)
                
                # 2. Narrower glow (medium alpha, medium width)
                glow_alpha_2 = int(140 * life)
                glow_color_2 = color + (glow_alpha_2,)
                pygame.draw.lines(temp_surf, glow_color_2, False, points, width=4)
                
                # 3. Bright core (high alpha, thin, white/light color)
                core_alpha = int(255 * life)
                core_color = (255, 255, 255, core_alpha)
                pygame.draw.lines(temp_surf, core_color, False, points, width=2)
                
            # Blit onto the screen centered at player tile center
            screen_x = px_center - cx + shake_x
            screen_y = py_center - cy + shake_y
            self._screen.blit(temp_surf, (screen_x, screen_y))

    def _draw_sidebar(self, player: Player):
        sx = MAP_PIXEL_WIDTH
        tx = sx + 20  # left text margin

        # Sidebar Panel Divider / Panel Background
        pygame.draw.rect(self._screen, ATARI_PANEL, (sx, 0, SIDEBAR_WIDTH, TOTAL_HEIGHT))
        pygame.draw.line(self._screen, ATARI_PANEL_BORDER, (sx, 0), (sx, TOTAL_HEIGHT), 2)

        LH = 30  # line height tuned for the larger DOS font
        y = 18

        # Header Status
        self._draw_text(tx, y, "-- STATUS --", color_rgb(Color.YELLOW), font=self._header_font); y += LH + 4
        self._draw_text(tx, y, f"Class: {getattr(player, 'char_class', 'Wizard')}", color_rgb(Color.CYAN), font=self._header_font); y += LH
        depth_str = "Overworld" if player.depth == 0 else f"{player.depth} (max {player.max_depth})"
        self._draw_text(tx, y, f"Depth: {depth_str}", color_rgb(Color.WHITE)); y += LH

        # HP bar (taller to fit the larger numerals)
        self._draw_text(tx, y, "HP:", color_rgb(Color.WHITE))
        hp_ratio = player.hp / player.max_hp
        bar_w, bar_h = 200, 26
        bx, by = sx + 70, y - 2

        pygame.draw.rect(self._screen, (45, 45, 50), (bx, by, bar_w, bar_h), border_radius=3)
        if hp_ratio <= 0.33:
            fill_c = color_rgb(Color.RED)
        elif hp_ratio <= 0.66:
            fill_c = color_rgb(Color.YELLOW)
        else:
            fill_c = color_rgb(Color.GREEN)
        if player.hp > 0:
            fill_w = max(4, int(bar_w * hp_ratio))
            pygame.draw.rect(self._screen, fill_c, (bx, by, fill_w, bar_h), border_radius=3)

        txt_hp = f"{player.hp}/{player.max_hp}"
        hp_surf = self._ui_font.render(txt_hp, True, (255, 255, 255))
        self._screen.blit(hp_surf, (bx + (bar_w - hp_surf.get_width()) // 2,
                                    by + (bar_h - hp_surf.get_height()) // 2))
        y += LH + 4

        # Status text details
        self._draw_text(tx, y, f"ATK:   {player.attack}", color_rgb(Color.WHITE)); y += LH
        self._draw_text(tx, y, f"Kills: {player.kills}", color_rgb(Color.WHITE)); y += LH

        arrows_text = f"Arrows: {getattr(player, 'arrows', 0)}"
        if getattr(player, "flame_arrows", 0) > 0:
            arrows_text += f" (Fire {player.flame_arrows})"
        self._draw_text(tx, y, arrows_text, color_rgb(Color.WHITE)); y += LH

        self._draw_text(tx, y, f"Gold:  {player.coins}", (240, 195, 30), font=self._header_font); y += LH
        self._draw_text(tx, y, f"Score: {player.score}", color_rgb(Color.CYAN), font=self._header_font); y += LH + 6

        # Keyboard Controls Cheat Sheet (short labels so they fit the wide font)
        self._draw_text(tx, y, "-- CONTROLS --", color_rgb(Color.YELLOW), font=self._header_font); y += LH + 2
        controls = [
            ("Arrows", "Move/Attack"),
            ("G", "Pick up"),
            ("I", "Inventory"),
            ("Z", "Zap wand"),
            ("Enter", "Use stairs"),
            ("Q", "Quit"),
        ]
        for key, desc in controls:
            self._draw_text(tx, y, f"{key:6} {desc}", color_rgb(Color.GRAY)); y += LH - 2

        # Equipment slots panel
        y += 6
        pygame.draw.line(self._screen, (35, 35, 45), (sx + 15, y), (sx + SIDEBAR_WIDTH - 15, y))
        y += 12

        self._draw_text(tx, y, "Weapon:", color_rgb(Color.YELLOW)); y += LH
        weapon_name = player.inventory.equipped_weapon.display_name if player.inventory.equipped_weapon else "(fists)"
        self._draw_text(tx, y, weapon_name, color_rgb(Color.CYAN), font=self._header_font); y += LH + 6

        self._draw_text(tx, y, "Wand:", color_rgb(Color.YELLOW)); y += LH
        wand_name = player.inventory.equipped_wand.display_name if player.inventory.equipped_wand else "(none)"
        self._draw_text(tx, y, wand_name, color_rgb(Color.MAGENTA), font=self._header_font)

    def _draw_log(self, log: MessageLog):
        y_top = MAP_PIXEL_HEIGHT
        
        # Message log border separator
        pygame.draw.rect(self._screen, (10, 14, 24), (0, y_top, MAP_PIXEL_WIDTH, LOG_HEIGHT))
        pygame.draw.line(self._screen, ATARI_PANEL_BORDER, (0, y_top), (MAP_PIXEL_WIDTH, y_top), 2)
        
        # Render rolling text messages
        row = 0
        curr_y = y_top + 12
        for text, color in log.recent:
            if row >= 4:
                break
            self._draw_text(15, curr_y, text, color_rgb(color), font=self._log_font)
            curr_y += 30
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

        # Modal Panel rect (wide enough for the larger DOS font, single column)
        w, h = 780, 470
        mx = (MAP_PIXEL_WIDTH - w) // 2
        my = (MAP_PIXEL_HEIGHT - h) // 2
        modal_rect = pygame.Rect(mx, my, w, h)

        # Modal shadow / border
        pygame.draw.rect(self._screen, (22, 25, 36), modal_rect, border_radius=8)
        pygame.draw.rect(self._screen, color_rgb(Color.CYAN), modal_rect, width=2, border_radius=8)

        # Inventory details header + control hints
        self._draw_text(mx + 25, my + 18, "-- INVENTORY --", color_rgb(Color.YELLOW), font=self._header_font)
        self._draw_text(mx + 25, my + 52, "Letter: equip/use (again = unequip)   Shift+Letter: drop",
                        color_rgb(Color.GRAY))
        self._draw_text(mx + 25, my + 76, "ESC: close inventory", color_rgb(Color.GRAY))
        pygame.draw.line(self._screen, (40, 45, 60), (mx + 20, my + 100), (mx + w - 20, my + 100), 2)

        items = player.inventory.items
        if not items:
            self._draw_text(mx + 240, my + 220, "(empty backpack)", color_rgb(Color.GRAY), font=self._header_font)
        else:
            col_w = w - 50
            row_h = 34
            max_rows = 10

            for i, item in enumerate(items[:max_rows]):
                letter = chr(ord("a") + i)
                item_x = mx + 25
                item_y = my + 114 + i * row_h

                # Check item parameters
                if item.kind.value == "healing_potion":
                    detail = f"heals {item.heal_amount}"
                elif item.kind.value == "weapon":
                    detail = f"+{item.attack_bonus} atk"
                elif item.kind.value == "wand":
                    detail = f"{item.wand_damage} dmg, {item.charges} chg"
                elif item.kind.value == "key":
                    detail = "opens locked chests"
                elif item.kind.value == "arrow":
                    detail = f"{item.charges} arrows"
                else:
                    detail = ""

                equipped = ""
                is_equipped = (item is player.inventory.equipped_weapon or item is player.inventory.equipped_wand)
                if is_equipped:
                    equipped = " (equipped)"

                # Render item slot box
                slot_rect = pygame.Rect(item_x, item_y, col_w, row_h - 6)
                bg_color = (35, 45, 75) if is_equipped else (26, 30, 45)
                border_color = color_rgb(Color.GREEN) if is_equipped else (45, 50, 70)
                pygame.draw.rect(self._screen, bg_color, slot_rect, border_radius=4)
                pygame.draw.rect(self._screen, border_color, slot_rect, width=1, border_radius=4)

                # Hotkey indicator label
                key_box = pygame.Rect(item_x + 6, item_y + 3, 26, row_h - 12)
                pygame.draw.rect(self._screen, (20, 22, 32), key_box, border_radius=3)
                key_surf = self._header_font.render(letter.upper(), True, color_rgb(Color.YELLOW))
                self._screen.blit(key_surf, (key_box.centerx - key_surf.get_width() // 2,
                                             key_box.centery - key_surf.get_height() // 2))

                # Item name and details text
                item_c = color_rgb(item.color)
                name_surf = self._ui_font.render(item.display_name, True, item_c)
                self._screen.blit(name_surf, (item_x + 44, item_y + 5))

                detail_c = color_rgb(Color.GREEN) if is_equipped else color_rgb(Color.GRAY)
                detail_surf = self._ui_font.render(f" [{detail}]{equipped}", True, detail_c)
                self._screen.blit(detail_surf, (item_x + 50 + name_surf.get_width(), item_y + 5))

            if len(items) > max_rows:
                self._draw_text(mx + 25, my + 114 + max_rows * row_h,
                                f"...and {len(items) - max_rows} more (drop some)", color_rgb(Color.GRAY))

    def _draw_shop_overlay(self, player: Player, merchant):
        # Create dark translucent screen overlay surface
        overlay = pygame.Surface((TOTAL_WIDTH, TOTAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self._screen.blit(overlay, (0, 0))

        # Modal Panel rect (widened for the larger DOS font)
        w, h = 780, 470
        mx = (MAP_PIXEL_WIDTH - w) // 2
        my = (MAP_PIXEL_HEIGHT - h) // 2
        modal_rect = pygame.Rect(mx, my, w, h)

        # Modal shadow / border (warm wood theme)
        pygame.draw.rect(self._screen, (28, 22, 16), modal_rect, border_radius=8)
        pygame.draw.rect(self._screen, (235, 180, 25), modal_rect, width=2, border_radius=8)

        # Header Title
        self._draw_text(mx + 25, my + 20, "-- MERCHANT SHOP --", (235, 180, 25), font=self._header_font)
        self._draw_text(mx + 25, my + 56, "Press 1-4 to buy.  ESC to exit.", (180, 180, 180))
        
        # Player Gold
        gold_text = f"Gold: {player.coins}g"
        gold_surf = self._header_font.render(gold_text, True, (235, 180, 25))
        self._screen.blit(gold_surf, (mx + w - gold_surf.get_width() - 25, my + 20))

        pygame.draw.line(self._screen, (65, 50, 40), (mx + 20, my + 90), (mx + w - 20, my + 90), 2)

        # 4 Shop Slots
        for i in range(4):
            item, price, is_sold_out = merchant.shop_items[i]

            slot_x = mx + 20
            slot_y = my + 102 + i * 88
            slot_w = w - 40
            slot_h = 78
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
                self._draw_weapon(icon_rect, icon_color, item.name)
            elif item.kind.value == "wand":
                self._draw_wand(icon_rect, icon_color)
            elif item.kind.value == "arrow":
                self._draw_arrows_item(icon_rect)
                
            # Item Name
            item_name = item.display_name.capitalize()
            name_color = color_rgb(item.color) if not is_sold_out else (120, 120, 120)
            name_surf = self._header_font.render(item_name, True, name_color)
            self._screen.blit(name_surf, (slot_x + 90, slot_y + 14))

            # Item description (kept short to fit the wide font)
            if item.name == "bless weapon":
                desc = "Blesses weapon. Can harm bosses."
            elif item.kind.value == "healing_potion":
                desc = f"Restores {item.heal_amount} HP when used."
            elif item.kind.value == "weapon":
                if item.name == "bow":
                    desc = f"Bow: shoots arrows. +{item.attack_bonus} atk."
                else:
                    desc = f"Melee weapon. +{item.attack_bonus} attack."
            elif item.kind.value == "wand":
                desc = f"Ranged zap, pierces. {item.wand_damage} dmg, {item.charges} chg."
            elif item.kind.value == "arrow":
                desc = f"Quiver of {item.charges} arrows. Use with a bow."
            else:
                desc = ""

            desc_color = (180, 180, 180) if not is_sold_out else (100, 100, 100)
            desc_surf = self._ui_font.render(desc, True, desc_color)
            self._screen.blit(desc_surf, (slot_x + 90, slot_y + 46))
            
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
        self._screen.fill((8, 10, 20))

        # Draw procedural background sparkles
        for _ in range(30):
            x = random.randint(10, TOTAL_WIDTH - 10)
            y = random.randint(10, TOTAL_HEIGHT - 10)
            size = random.choice([1, 2])
            pygame.draw.circle(self._screen, (66, 96, 150), (x, y), size)

        # Big Title Logo
        t_surf = self._title_font.render("ARCADE DUNGEON", True, ATARI_NEON_YELLOW)
        self._screen.blit(t_surf, ((TOTAL_WIDTH - t_surf.get_width()) // 2, 80))
        
        st_surf = self._header_font.render("1983-STYLE PIXEL CRAWLER", True, ATARI_NEON_CYAN)
        self._screen.blit(st_surf, ((TOTAL_WIDTH - st_surf.get_width()) // 2, 140))

        # Draw a line divider
        pygame.draw.line(self._screen, ATARI_PANEL_BORDER, (TOTAL_WIDTH // 4, 180), (TOTAL_WIDTH * 3 // 4, 180), 2)

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

        self._screen.blit(self._crt_overlay, (0, 0))
        pygame.display.flip()

    def render_class_select(self, selected_class_idx: int):
        self._frame_count += 1  # advance so the hero previews animate
        self._screen.fill((8, 10, 20))

        # Background sparkles
        for _ in range(30):
            x = random.randint(10, TOTAL_WIDTH - 10)
            y = random.randint(10, TOTAL_HEIGHT - 10)
            size = random.choice([1, 2])
            pygame.draw.circle(self._screen, (66, 96, 150), (x, y), size)

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

        card_w, card_h = 372, 380
        card_y = 160
        gap = 24
        start_x = (TOTAL_WIDTH - (3 * card_w + 2 * gap)) // 2

        for idx, data in enumerate(classes_data):
            card_x = start_x + idx * (card_w + gap)
            card_rect = pygame.Rect(card_x, card_y, card_w, card_h)

            selected = (idx == selected_class_idx)
            
            # Select background and border colors
            if selected:
                bg_color = (26, 24, 40)
                border_color = ATARI_NEON_ORANGE
                border_width = 3
            else:
                bg_color = (16, 16, 28)
                border_color = (56, 70, 108)
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

            # Animated pixel-art hero preview (same sprite used in-game),
            # scaled up 4x with nearest-neighbor so it stays crisp & chunky.
            icon_center_x = card_x + card_w // 2
            icon_center_y = card_y + 160

            sheet = self._player_sheets.get(data["name"].lower())
            if sheet:
                # Cycle the DOWN-facing walk frames so the preview struts.
                frame = (self._frame_count // 8) % 4
                src = pygame.Rect(frame * 32, 0, 32, 32)
                icon = pygame.Surface((32, 32), pygame.SRCALPHA)
                icon.blit(sheet, (0, 0), src)
                icon = pygame.transform.scale(icon, (128, 128))  # 4x, nearest
                self._screen.blit(icon, (icon_center_x - 64, icon_center_y - 64))

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

        self._screen.blit(self._crt_overlay, (0, 0))
        pygame.display.flip()

    def render_game_over(self, player: Player, highscores: list):
        self._screen.fill((22, 10, 14))

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

        self._screen.blit(self._crt_overlay, (0, 0))
        pygame.display.flip()
