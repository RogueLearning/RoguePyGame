import sys
import math
import random
import pygame

from Entities.player import Player
from Map.dungeon_level import DungeonLevel
from Map.tile import TileType
from UI.colors import Color, color_rgb
from UI.message_log import MessageLog
from UI.sprites import get_game_sprites

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
        pygame.display.set_caption("Rogue PyGame - 8-Bit Retro Arcade")

        # Compile game sprites
        self._sprites = get_game_sprites()

        # Fonts
        self._init_fonts()

        # Animation states
        self._entity_positions = {}  # entity -> [current_x, current_y]
        self._bumps = {}            # entity -> {"dx": dx, "dy": dy, "progress": 0.0, "speed": 0.15}
        self._projectiles = []       # list of dicts
        self._damage_texts = []      # list of dicts
        self._particles = []         # list of dicts
        
        self._shake_intensity = 0.0
        self._shake_decay = 0.85
        self._frame_count = 0

        # Slash & Flash Animation states
        self._slashes = []
        self._flash_alpha = 0.0
        self._flash_color = (255, 255, 255)

        # Pre-compile the CRT Scanlines & Bezel Surface
        self._init_crt_surface()

    def _init_fonts(self):
        self._ui_font = None
        font_name = None
        # Try classic retro/monospace fonts first
        for name in ["press start 2p", "vt323", "monaco", "courier new", "courier", "arial"]:
            try:
                size = 11 if "press start" in name.lower() or "vt323" in name.lower() else 15
                self._ui_font = pygame.font.SysFont(name, size)
                if self._ui_font:
                    font_name = name
                    break
            except Exception:
                pass
        if not self._ui_font:
            self._ui_font = pygame.font.SysFont(None, 16)

        # Bold headers
        header_size = 14 if "press start" in font_name.lower() or "vt323" in font_name.lower() else 18
        self._header_font = pygame.font.SysFont(font_name, header_size, bold=True)
        
        # Title font
        title_size = 32 if "press start" in font_name.lower() or "vt323" in font_name.lower() else 42
        self._title_font = pygame.font.SysFont(font_name, title_size, bold=True)
        
        # Log font - monospaced is nice
        self._log_font = self._ui_font

    def _init_crt_surface(self):
        self._crt_surface = pygame.Surface((TOTAL_WIDTH, TOTAL_HEIGHT), pygame.SRCALPHA)
        # Scanlines (dark horizontal line every 2 pixels)
        for y in range(0, TOTAL_HEIGHT, 2):
            pygame.draw.line(self._crt_surface, (0, 0, 0, 35), (0, y), (TOTAL_WIDTH, y))
        
        # Subtle horizontal bezel gradient on edges (vignette glow)
        for x in range(12):
            alpha = int(140 * (1.0 - x / 12.0))
            pygame.draw.line(self._crt_surface, (0, 0, 0, alpha), (x, 0), (x, TOTAL_HEIGHT))
            pygame.draw.line(self._crt_surface, (0, 0, 0, alpha), (TOTAL_WIDTH - 1 - x, 0), (TOTAL_WIDTH - 1 - x, TOTAL_HEIGHT))
        for y in range(12):
            alpha = int(140 * (1.0 - y / 12.0))
            pygame.draw.line(self._crt_surface, (0, 0, 0, alpha), (0, y), (TOTAL_WIDTH, y))
            pygame.draw.line(self._crt_surface, (0, 0, 0, alpha), (0, TOTAL_HEIGHT - 1 - y), (TOTAL_WIDTH, TOTAL_HEIGHT - 1 - y))

    def reset(self):
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
            "speed": 0.45 if type == "lightning" else 0.35,
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
            dt["y"] -= 0.5
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
                        "size": random.uniform(2, 3),
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
                        "size": random.uniform(2, 4),
                        "life": random.uniform(0.2, 0.4),
                        "max_life": 1.0
                    })

            if proj["index"] >= len(path) - 1:
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

        # Render Melee Slashes
        self._draw_slashes(shake_x, shake_y)

        # Render Projectiles (Visuals)
        self._draw_projectiles(shake_x, shake_y)

        # Render Particles
        self._draw_particles(shake_x, shake_y)

        # Render Damage text overlay
        self._draw_damage_texts(shake_x, shake_y)

        # Render Screen Flash Overlay
        if self._flash_alpha > 0:
            flash_surf = pygame.Surface((MAP_PIXEL_WIDTH, MAP_PIXEL_HEIGHT), pygame.SRCALPHA)
            flash_color_with_alpha = self._flash_color + (int(self._flash_alpha),)
            flash_surf.fill(flash_color_with_alpha)
            self._screen.blit(flash_surf, (0, 0))

        # Render Sidebar
        self._draw_sidebar(player)

        # Render Message Log
        self._draw_log(log)

        # Draw inventory modal if requested
        if show_inventory:
            self._draw_inventory_overlay(player)

        # Draw shop modal if requested
        if show_shop:
            self._draw_shop_overlay(player, show_shop)

        # Apply CRT Scanline Filter Overlay (Bezel + Scanlines)
        self._screen.blit(self._crt_surface, (0, 0))

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
                visible = t.visible

                if is_overworld:
                    in_town = (x < 15 and y < 9)
                    in_farm = (x >= 15 and y < 9)
                    in_cemetery = (x < 15 and y >= 9)
                    in_field = (x >= 15 and y >= 9)
                    
                    if t.type == TileType.WALL:
                        if in_town:
                            self._draw_wooden_wall(rect, (0,0,0))
                        elif in_farm:
                            self._draw_fence(rect, (0,0,0))
                        elif in_cemetery:
                            self._draw_stone_wall(rect, (0,0,0))
                        else:
                            self._draw_hedge(rect, (0,0,0))
                            
                    elif t.type == TileType.FLOOR:
                        if in_town:
                            self._draw_cobblestone(rect, (0,0,0), visible)
                        elif in_farm:
                            self._draw_tilled_soil(rect, (0,0,0), visible)
                        elif in_cemetery:
                            self._draw_dark_grass(rect, (0,0,0), visible)
                        else:
                            self._draw_grass(rect, (0,0,0), visible)
                            
                    elif t.type == TileType.STAIRS_DOWN:
                        if in_farm:
                            self._draw_cellar_hatch(rect, visible)
                        elif in_cemetery:
                            self._draw_crypt_entrance(rect, visible)
                        else:
                            self._draw_cave_entrance(rect, visible)
                else:
                    if t.type == TileType.WALL:
                        self._draw_brick_wall(rect, (0,0,0))
                    elif t.type == TileType.FLOOR:
                        self._draw_floor(rect, (0,0,0), visible)
                    elif t.type == TileType.STAIRS_DOWN:
                        self._draw_stairs_down(rect, (0,0,0))
                    elif t.type == TileType.STAIRS_UP:
                        self._draw_stairs_up(rect, (0,0,0))
                    elif t.type == TileType.FOUNTAIN:
                        self._draw_fountain(rect, visible)

                # Explorer dim-mask overlay for explored but out-of-sight tiles
                if not visible:
                    shadow = pygame.Surface((TILE_SIZE, TILE_SIZE))
                    shadow.fill((0, 0, 0))
                    shadow.set_alpha(150)
                    self._screen.blit(shadow, rect.topleft)

    def _draw_wooden_wall(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["tile_wall_wood"], rect.topleft)

    def _draw_fence(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["tile_wall_fence"], rect.topleft)

    def _draw_stone_wall(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["tile_wall_stone"], rect.topleft)

    def _draw_hedge(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["tile_wall_hedge"], rect.topleft)

    def _draw_cobblestone(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        self._screen.blit(self._sprites["tile_floor_cobble"], rect.topleft)

    def _draw_tilled_soil(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        self._screen.blit(self._sprites["tile_floor_soil"], rect.topleft)

    def _draw_dark_grass(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        self._screen.blit(self._sprites["tile_floor_cemetery"], rect.topleft)

    def _draw_grass(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        self._screen.blit(self._sprites["tile_floor_grass"], rect.topleft)

    def _draw_cellar_hatch(self, rect: pygame.Rect, visible: bool):
        self._screen.blit(self._sprites["tile_stairs_cellar"], rect.topleft)

    def _draw_crypt_entrance(self, rect: pygame.Rect, visible: bool):
        self._screen.blit(self._sprites["tile_stairs_crypt"], rect.topleft)

    def _draw_cave_entrance(self, rect: pygame.Rect, visible: bool):
        self._screen.blit(self._sprites["tile_stairs_cave"], rect.topleft)

    def _draw_brick_wall(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["tile_wall_dungeon"], rect.topleft)

    def _draw_floor(self, rect: pygame.Rect, color: tuple[int, int, int], visible: bool):
        self._screen.blit(self._sprites["tile_floor_dungeon"], rect.topleft)

    def _draw_stairs_down(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["tile_stairs_down"], rect.topleft)

    def _draw_stairs_up(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["tile_stairs_up"], rect.topleft)

    def _draw_fountain(self, rect: pygame.Rect, visible: bool):
        frame = (self._frame_count // 15) % 2
        self._screen.blit(self._sprites[f"tile_fountain_{frame}"], rect.topleft)

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
                pygame.draw.rect(self._screen, color, rect.inflate(-10, -10), border_radius=1)

    def _draw_key(self, rect: pygame.Rect):
        self._screen.blit(self._sprites["item_key"], rect.topleft)

    def _draw_coin(self, rect: pygame.Rect):
        frame = (self._frame_count // 8) % 4
        self._screen.blit(self._sprites[f"item_coin_{frame}"], rect.topleft)

    def _draw_potion(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["item_potion"], rect.topleft)

    def _draw_weapon(self, rect: pygame.Rect, color: tuple[int, int, int], name: str = ""):
        if name == "bow":
            self._screen.blit(self._sprites["item_bow"], rect.topleft)
        else:
            self._screen.blit(self._sprites["item_weapon"], rect.topleft)

    def _draw_arrows_item(self, rect: pygame.Rect):
        self._screen.blit(self._sprites["item_arrow"], rect.topleft)

    def _draw_wand(self, rect: pygame.Rect, color: tuple[int, int, int]):
        self._screen.blit(self._sprites["item_wand"], rect.topleft)

    def _draw_entities(self, level: DungeonLevel, player: Player, shake_x: int, shake_y: int):
        # Render Monsters
        for m in level.monsters:
            if not m.is_alive:
                continue
            if m.x >= MAP_WIDTH or m.y >= MAP_HEIGHT:
                continue
            if not level.tiles[m.x][m.y].visible:
                continue

            vx, vy = self._get_interpolated_pos(m)
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
        cur[0] += (target_x - cur[0]) * 0.28
        cur[1] += (target_y - cur[1]) * 0.28
        
        if math.hypot(target_x - cur[0], target_y - cur[1]) < 0.5:
            cur[0], cur[1] = target_x, target_y

        return cur[0], cur[1]

    def _get_bump_offset(self, entity) -> tuple[float, float]:
        if entity not in self._bumps:
            return 0.0, 0.0
            
        bump = self._bumps[entity]
        factor = math.sin(bump["progress"] * math.pi)
        ox = bump["dx"] * TILE_SIZE * 0.5 * factor
        oy = bump["dy"] * TILE_SIZE * 0.5 * factor
        return ox, oy

    def _draw_monster_sprite(self, rect: pygame.Rect, name: str, color: tuple[int, int, int]):
        sprite_key = name.lower().replace(" ", "_")
        # 2-frame walking/breathing cycle
        frame = (self._frame_count // 18) % 2
        sprite = self._sprites.get(f"monster_{sprite_key}_{frame}")
        if sprite:
            self._screen.blit(sprite, rect.topleft)
        else:
            pygame.draw.rect(self._screen, color, rect.inflate(-6, -6))

    def _draw_player_sprite(self, rect: pygame.Rect, color: tuple[int, int, int], enchanted: bool, player: Player = None):
        # Glow ring border if enchanted
        if enchanted:
            pygame.draw.rect(self._screen, (235, 195, 45), rect.inflate(4, 4), 2)

        char_class = "Wizard"
        facing = "DOWN"
        if player:
            if hasattr(player, "char_class"):
                char_class = player.char_class
            if hasattr(player, "facing"):
                facing = player.facing

        # Determine walk frame
        is_moving = False
        if player and player in self._entity_positions:
            vx, vy = self._entity_positions[player]
            tx, ty = player.x * TILE_SIZE, player.y * TILE_SIZE
            is_moving = (math.hypot(tx - vx, ty - vy) > 0.5)
            
        frame_idx = 0
        if is_moving:
            frame_idx = (self._frame_count // 6) % 4

        class_key = char_class.lower()
        facing_key = facing.lower()
        sprite_name = f"player_{class_key}_{facing_key}_{frame_idx}"
        
        sprite = self._sprites.get(sprite_name, self._sprites.get("player_wizard_down_0"))
        if sprite:
            self._screen.blit(sprite, rect.topleft)

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
                dx = path[1][0] - path[0][0] if len(path) > 1 else 0
                dy = path[1][1] - path[0][1] if len(path) > 1 else 0
                
                player_x = (path[0][0] - dx + 0.5) * TILE_SIZE + shake_x
                player_y = (path[0][1] - dy + 0.5) * TILE_SIZE + shake_y
                
                # Electrical bolts drawn thick and blocky
                points = [(player_x, player_y)]
                dist = math.hypot(px - player_x, py - player_y)
                num_segments = max(4, int(dist / 8))
                
                for i in range(1, num_segments):
                    t = i / num_segments
                    lx = player_x + (px - player_x) * t
                    ly = player_y + (py - player_y) * t
                    
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
                    pygame.draw.lines(self._screen, (100, 200, 255), False, points, 4)
                    pygame.draw.lines(self._screen, (255, 255, 255), False, points, 2)
            else:
                # 8-bit fireball sprite
                frame = (self._frame_count // 5) % 2
                self._screen.blit(self._sprites[f"proj_fireball_{frame}"], (int(px - 16), int(py - 16)))

    def _draw_particles(self, shake_x: int, shake_y: int):
        for p in self._particles:
            alpha = int(max(0, min(255, (p["life"] / p["max_life"]) * 255)))
            color_with_alpha = p["color"] + (alpha,)
            
            # Temporary surface for transparent square particles
            surf = pygame.Surface((p["size"] * 2, p["size"] * 2), pygame.SRCALPHA)
            pygame.draw.rect(surf, color_with_alpha, (0, 0, p["size"] * 2, p["size"] * 2))
            
            self._screen.blit(surf, (p["x"] - p["size"] + shake_x, p["y"] - p["size"] + shake_y))

    def _draw_damage_texts(self, shake_x: int, shake_y: int):
        for dt in self._damage_texts:
            alpha = int(max(0, min(255, (dt["life"] / dt["max_life"]) * 255)))
            txt_surf = self._header_font.render(dt["text"], True, dt["color"])
            
            alpha_surf = pygame.Surface(txt_surf.get_size(), pygame.SRCALPHA)
            alpha_surf.fill((255, 255, 255, alpha))
            alpha_surf.blit(txt_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            tx = dt["x"] - alpha_surf.get_width() // 2 + shake_x
            ty = dt["y"] - 15 + shake_y
            self._screen.blit(alpha_surf, (tx, ty))

    def _draw_slashes(self, shake_x: int, shake_y: int):
        for s in self._slashes:
            tx, ty = s["x"], s["y"]
            direction = s["direction"]
            color = s["color"]
            life = s["life"]
            
            px, py = tx, ty
            if direction == "RIGHT":
                px = tx - 1
            elif direction == "LEFT":
                px = tx + 1
            elif direction == "UP":
                py = ty + 1
            elif direction == "DOWN":
                py = ty - 1
                
            px_center = int((px + 0.5) * TILE_SIZE)
            py_center = int((py + 0.5) * TILE_SIZE)
            R = int(TILE_SIZE * 0.95)
            
            temp_surf = pygame.Surface((120, 120), pygame.SRCALPHA)
            cx, cy = 60, 60
            
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
                
            half_sweep = math.radians(50)
            num_segments = 12
            
            points = []
            for i in range(num_segments + 1):
                angle = center_angle - half_sweep + (2.0 * half_sweep * i / num_segments)
                x_p = int(cx + R * math.cos(angle))
                y_p = int(cy - R * math.sin(angle))
                points.append((x_p, y_p))
                
            if len(points) > 1:
                glow_alpha_1 = int(70 * life)
                glow_color_1 = color + (glow_alpha_1,)
                pygame.draw.lines(temp_surf, glow_color_1, False, points, width=6)
                
                glow_alpha_2 = int(140 * life)
                glow_color_2 = color + (glow_alpha_2,)
                pygame.draw.lines(temp_surf, glow_color_2, False, points, width=4)
                
                core_alpha = int(255 * life)
                core_color = (255, 255, 255, core_alpha)
                pygame.draw.lines(temp_surf, core_color, False, points, width=2)
                
            screen_x = px_center - cx + shake_x
            screen_y = py_center - cy + shake_y
            self._screen.blit(temp_surf, (screen_x, screen_y))

    def _draw_sidebar(self, player: Player):
        sx = MAP_PIXEL_WIDTH
        
        pygame.draw.rect(self._screen, (20, 20, 26), (sx, 0, SIDEBAR_WIDTH, TOTAL_HEIGHT))
        pygame.draw.line(self._screen, (40, 40, 50), (sx, 0), (sx, TOTAL_HEIGHT), 2)

        self._draw_text(sx + 20, 20, "-- STATUS --", color_rgb(Color.YELLOW), font=self._header_font)
        self._draw_text(sx + 20, 48, f"Class: {getattr(player, 'char_class', 'Wizard')}", color_rgb(Color.CYAN), font=self._header_font)
        depth_str = "Overworld" if player.depth == 0 else str(player.depth)
        self._draw_text(sx + 20, 76, f"Depth: {depth_str} (max {player.max_depth})", color_rgb(Color.WHITE))

        self._draw_text(sx + 20, 106, "HP: ", color_rgb(Color.WHITE))
        hp_ratio = player.hp / player.max_hp
        bar_w = 180
        bar_h = 16
        bx = sx + 60
        by = 106
        
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
        self._screen.blit(hp_surf, (bx + (bar_w - hp_surf.get_width()) // 2, by - 1))

        self._draw_text(sx + 20, 136, f"ATK:   {player.attack}", color_rgb(Color.WHITE))
        self._draw_text(sx + 20, 166, f"Kills: {player.kills}", color_rgb(Color.WHITE))
        
        arrows_text = f"Arrows: {getattr(player, 'arrows', 0)}"
        if getattr(player, "flame_arrows", 0) > 0:
            arrows_text += f"  (Fire: {player.flame_arrows})"
        self._draw_text(sx + 20, 196, arrows_text, color_rgb(Color.WHITE))
        
        self._draw_text(sx + 20, 226, f"Gold:  {player.coins}g", (240, 195, 30), font=self._header_font)
        self._draw_text(sx + 20, 256, f"Score: {player.score}", color_rgb(Color.CYAN), font=self._header_font)

        self._draw_text(sx + 20, 286, "-- CONTROLS --", color_rgb(Color.YELLOW), font=self._header_font)
        controls = [
            ("Arrows", "Move / Bump Attack"),
            ("G Key", "Pick up item"),
            ("I Key", "Open Inventory"),
            ("Z Key", "Zap wand (+ Arrow)"),
            ("Enter", "Use stairs"),
            ("Q Key", "Quit game"),
        ]
        curr_y = 316
        for key, desc in controls:
            self._draw_text(sx + 20, curr_y, f"{key:6}: {desc}", color_rgb(Color.GRAY))
            curr_y += 24

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
        
        pygame.draw.rect(self._screen, (10, 10, 14), (0, y_top, MAP_PIXEL_WIDTH, LOG_HEIGHT))
        pygame.draw.line(self._screen, (40, 40, 50), (0, y_top), (MAP_PIXEL_WIDTH, y_top), 2)
        
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
        overlay = pygame.Surface((TOTAL_WIDTH, TOTAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self._screen.blit(overlay, (0, 0))

        w, h = 540, 420
        mx = (MAP_PIXEL_WIDTH - w) // 2
        my = (MAP_PIXEL_HEIGHT - h) // 2
        modal_rect = pygame.Rect(mx, my, w, h)
        
        pygame.draw.rect(self._screen, (22, 25, 36), modal_rect, border_radius=8)
        pygame.draw.rect(self._screen, color_rgb(Color.CYAN), modal_rect, width=2, border_radius=8)

        self._draw_text(mx + 25, my + 20, "-- INVENTORY --", color_rgb(Color.YELLOW), font=self._header_font)
        self._draw_text(mx + 25, my + 45, "Press item [ a - t ] to use/equip, any other key to cancel", color_rgb(Color.GRAY))
        pygame.draw.line(self._screen, (40, 45, 60), (mx + 20, my + 75), (mx + w - 20, my + 75), 2)

        items = player.inventory.items
        if not items:
            self._draw_text(mx + 180, my + 180, "(empty backpack)", color_rgb(Color.GRAY), font=self._header_font)
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
                
                if item.kind.value == "healing_potion":
                    detail = f"heals {item.heal_amount}"
                elif item.kind.value == "weapon":
                    detail = f"+{item.attack_bonus} atk"
                elif item.kind.value == "wand":
                    detail = f"{item.wand_damage} dmg, {item.charges} chg"
                elif item.kind.value == "key":
                    detail = "opens chests"
                elif item.kind.value == "arrow":
                    detail = f"{item.charges} arrows"
                else:
                    detail = ""

                equipped = ""
                is_equipped = (item is player.inventory.equipped_weapon or item is player.inventory.equipped_wand)
                if is_equipped:
                    equipped = " (equipped)"
                
                slot_rect = pygame.Rect(item_x, item_y, col_w, row_h - 4)
                bg_color = (35, 45, 75) if is_equipped else (26, 30, 45)
                border_color = color_rgb(Color.GREEN) if is_equipped else (45, 50, 70)
                pygame.draw.rect(self._screen, bg_color, slot_rect, border_radius=4)
                pygame.draw.rect(self._screen, border_color, slot_rect, width=1, border_radius=4)

                key_surf = self._header_font.render(f" {letter.upper()} ", True, color_rgb(Color.YELLOW))
                pygame.draw.rect(self._screen, (20, 22, 32), (item_x + 4, item_y + 3, 20, 18), border_radius=2)
                self._screen.blit(key_surf, (item_x + 6, item_y + 2))

                item_c = color_rgb(item.color)
                name_surf = self._ui_font.render(item.display_name, True, item_c)
                self._screen.blit(name_surf, (item_x + 30, item_y + 3))

                detail_c = color_rgb(Color.GREEN) if is_equipped else color_rgb(Color.GRAY)
                detail_surf = self._ui_font.render(f" [{detail}]{equipped}", True, detail_c)
                self._screen.blit(detail_surf, (item_x + 30 + name_surf.get_width(), item_y + 3))

    def _draw_shop_overlay(self, player: Player, merchant):
        overlay = pygame.Surface((TOTAL_WIDTH, TOTAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self._screen.blit(overlay, (0, 0))

        w, h = 540, 436
        mx = (MAP_PIXEL_WIDTH - w) // 2
        my = (MAP_PIXEL_HEIGHT - h) // 2
        modal_rect = pygame.Rect(mx, my, w, h)
        
        pygame.draw.rect(self._screen, (28, 22, 16), modal_rect, border_radius=8)
        pygame.draw.rect(self._screen, (235, 180, 25), modal_rect, width=2, border_radius=8)

        self._draw_text(mx + 25, my + 20, "-- MERCHANT SHOP --", (235, 180, 25), font=self._header_font)
        self._draw_text(mx + 25, my + 45, "Keys [ 1 - 4 ] or [ a - d ] to buy. ESC to close.", (180, 180, 180))
        
        gold_text = f"Your Gold: {player.coins}g"
        gold_surf = self._header_font.render(gold_text, True, (235, 180, 25))
        self._screen.blit(gold_surf, (mx + w - gold_surf.get_width() - 25, my + 20))
        
        pygame.draw.line(self._screen, (65, 50, 40), (mx + 20, my + 75), (mx + w - 20, my + 75), 2)

        for i in range(4):
            item, price, is_sold_out = merchant.shop_items[i]
            
            slot_x = mx + 20
            slot_y = my + 90 + i * 80
            slot_w = w - 40
            slot_h = 70
            slot_rect = pygame.Rect(slot_x, slot_y, slot_w, slot_h)
            
            if is_sold_out:
                bg_color = (18, 16, 15)
                border_color = (45, 40, 38)
            else:
                bg_color = (36, 30, 26)
                border_color = (65, 52, 42)
                
            pygame.draw.rect(self._screen, bg_color, slot_rect, border_radius=6)
            pygame.draw.rect(self._screen, border_color, slot_rect, width=1, border_radius=6)
            
            key_box_rect = pygame.Rect(slot_x + 10, slot_y + 15, 24, 24)
            pygame.draw.rect(self._screen, (24, 20, 18), key_box_rect, border_radius=4)
            pygame.draw.rect(self._screen, (235, 180, 25) if not is_sold_out else (100, 100, 100), key_box_rect, width=1, border_radius=4)
            
            key_surf = self._header_font.render(str(i + 1), True, (235, 180, 25) if not is_sold_out else (120, 120, 120))
            self._screen.blit(key_surf, (key_box_rect.centerx - key_surf.get_width() // 2, key_box_rect.centery - key_surf.get_height() // 2))
            
            icon_rect = pygame.Rect(slot_x + 45, slot_y + (slot_h - 32) // 2, 32, 32)
            icon_color = color_rgb(item.color)
            if is_sold_out:
                icon_color = (80, 80, 80)
            
            if item.name == "bless weapon":
                star_color = (255, 215, 0) if not is_sold_out else (80, 80, 80)
                pygame.draw.rect(self._screen, star_color, icon_rect.inflate(-8, -8), 2)
            elif item.kind.value == "healing_potion":
                self._draw_potion(icon_rect, icon_color)
            elif item.kind.value == "weapon":
                self._draw_weapon(icon_rect, icon_color, item.name)
            elif item.kind.value == "wand":
                self._draw_wand(icon_rect, icon_color)
            elif item.kind.value == "arrow":
                self._draw_arrows_item(icon_rect)
                
            item_name = item.display_name.capitalize()
            name_color = color_rgb(item.color) if not is_sold_out else (120, 120, 120)
            name_surf = self._header_font.render(item_name, True, name_color)
            self._screen.blit(name_surf, (slot_x + 90, slot_y + 12))
            
            if item.name == "bless weapon":
                desc = "Blesses equipped weapon. Needed to harm the boss."
            elif item.kind.value == "healing_potion":
                desc = f"Restores {item.heal_amount} HP. Consumed from inventory."
            elif item.kind.value == "weapon":
                if item.name == "bow":
                    desc = f"Ranged weapon: shoots arrows up to 10 cells (+{item.attack_bonus} atk)."
                else:
                    desc = f"Melee weapon: provides +{item.attack_bonus} attack bonus."
            elif item.kind.value == "wand":
                desc = f"Ranged zap. Pierces. Deals {item.wand_damage} dmg. {item.charges} chg."
            elif item.kind.value == "arrow":
                desc = f"Quiver of {item.charges} arrows. Used with a Bow."
            else:
                desc = ""
                
            desc_color = (180, 180, 180) if not is_sold_out else (100, 100, 100)
            desc_surf = self._ui_font.render(desc, True, desc_color)
            self._screen.blit(desc_surf, (slot_x + 90, slot_y + 40))
            
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

        # Starry procedural arcade background
        for _ in range(30):
            x = random.randint(10, TOTAL_WIDTH - 10)
            y = random.randint(10, TOTAL_HEIGHT - 10)
            size = random.choice([1, 2])
            pygame.draw.rect(self._screen, (70, 70, 90), (x, y, size * 2, size * 2))

        # Pulsing game title
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
        yellow_pulse = (int(180 + 75 * pulse), int(150 + 85 * pulse), 45)
        
        t_surf = self._title_font.render("WIZARD'S DUNGEON", True, yellow_pulse)
        self._screen.blit(t_surf, ((TOTAL_WIDTH - t_surf.get_width()) // 2, 80))
        
        st_surf = self._header_font.render("8-Bit Retro Pygame Roguelike", True, color_rgb(Color.CYAN))
        self._screen.blit(st_surf, ((TOTAL_WIDTH - st_surf.get_width()) // 2, 140))

        pygame.draw.line(self._screen, (40, 50, 75), (TOTAL_WIDTH // 4, 180), (TOTAL_WIDTH * 3 // 4, 180), 2)

        hs_x = (TOTAL_WIDTH - 400) // 2
        self._draw_text(hs_x, 220, "--- HIGH SCORES ---", color_rgb(Color.YELLOW), font=self._header_font)
        
        curr_y = 260
        if not highscores:
            self._draw_text(hs_x + 80, curr_y + 40, "(no runs recorded yet)", color_rgb(Color.GRAY))
        else:
            for rank, entry in enumerate(highscores[:8], start=1):
                score, depth, kills, date_obj = entry
                txt = f"{rank:>2}. Score: {score:>5} | Depth: {depth:>2} | Kills: {kills:>3}"
                self._draw_text(hs_x, curr_y, txt, color_rgb(Color.WHITE))
                curr_y += 26

        # Pulsing click start text
        start_pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
        green_pulse = (int(46 + 150 * start_pulse), int(196 + 59 * start_pulse), int(120 + 80 * start_pulse))
        p_surf = self._header_font.render("Press ENTER to Begin the Quest", True, green_pulse)
        self._screen.blit(p_surf, ((TOTAL_WIDTH - p_surf.get_width()) // 2, 600))
        
        exit_surf = self._ui_font.render("Press Q to Quit", True, color_rgb(Color.GRAY))
        self._screen.blit(exit_surf, ((TOTAL_WIDTH - exit_surf.get_width()) // 2, 640))

        # Apply scanlines overlay
        self._screen.blit(self._crt_surface, (0, 0))
        pygame.display.flip()

    def render_class_select(self, selected_class_idx: int):
        self._screen.fill((10, 10, 14))

        for _ in range(30):
            x = random.randint(10, TOTAL_WIDTH - 10)
            y = random.randint(10, TOTAL_HEIGHT - 10)
            size = random.choice([1, 2])
            pygame.draw.rect(self._screen, (70, 70, 90), (x, y, size * 2, size * 2))

        title_surf = self._title_font.render("SELECT YOUR HERO CLASS", True, color_rgb(Color.YELLOW))
        self._screen.blit(title_surf, ((TOTAL_WIDTH - title_surf.get_width()) // 2, 70))

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
                "key_hint": "Press 1 / K to Select",
                "sprite_name": "player_knight_down_0"
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
                "key_hint": "Press 2 / W to Select",
                "sprite_name": "player_wizard_down_0"
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
                "key_hint": "Press 3 / R to Select",
                "sprite_name": "player_rogue_down_0"
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

            name_surf = self._header_font.render(data["name"], True, border_color if selected else (200, 200, 200))
            self._screen.blit(name_surf, (card_x + (card_w - name_surf.get_width()) // 2, card_y + 20))

            hp_surf = self._ui_font.render(data["hp"], True, (255, 255, 255))
            self._screen.blit(hp_surf, (card_x + (card_w - hp_surf.get_width()) // 2, card_y + 55))
            
            wpn_surf = self._ui_font.render(data["weapon"], True, color_rgb(Color.CYAN))
            self._screen.blit(wpn_surf, (card_x + (card_w - wpn_surf.get_width()) // 2, card_y + 75))

            # Render compiled sprite scaled up to 96x96 inside card
            icon_center_x = card_x + card_w // 2
            icon_center_y = card_y + 160
            sprite = self._sprites.get(data["sprite_name"])
            if sprite:
                scaled_sprite = pygame.transform.scale(sprite, (96, 96))
                self._screen.blit(scaled_sprite, (icon_center_x - 48, icon_center_y - 48))

            desc_y = card_y + 230
            for desc_line in data["desc"]:
                d_surf = self._ui_font.render(desc_line, True, (170, 170, 175))
                self._screen.blit(d_surf, (card_x + (card_w - d_surf.get_width()) // 2, desc_y))
                desc_y += 20

            k_surf = self._ui_font.render(data["key_hint"], True, color_rgb(Color.GRAY))
            self._screen.blit(k_surf, (card_x + (card_w - k_surf.get_width()) // 2, card_y + 345))

        nav_text = "Use LEFT / RIGHT arrows or A / D to navigate. Press ENTER to select."
        nav_surf = self._header_font.render(nav_text, True, color_rgb(Color.GREEN))
        self._screen.blit(nav_surf, ((TOTAL_WIDTH - nav_surf.get_width()) // 2, 560))
        
        esc_surf = self._ui_font.render("Press ESC to return to Title Screen", True, color_rgb(Color.GRAY))
        self._screen.blit(esc_surf, ((TOTAL_WIDTH - esc_surf.get_width()) // 2, 600))

        self._screen.blit(self._crt_surface, (0, 0))
        pygame.display.flip()

    def render_game_over(self, player: Player, highscores: list):
        self._screen.fill((15, 10, 10))

        go_surf = self._title_font.render("GAME OVER", True, color_rgb(Color.RED))
        self._screen.blit(go_surf, ((TOTAL_WIDTH - go_surf.get_width()) // 2, 70))

        self._draw_text(TOTAL_WIDTH // 4, 150, f"Max depth reached:  {player.max_depth}", color_rgb(Color.WHITE), font=self._header_font)
        self._draw_text(TOTAL_WIDTH // 4, 185, f"Monsters defeated:  {player.kills}", color_rgb(Color.WHITE), font=self._header_font)
        self._draw_text(TOTAL_WIDTH // 4, 220, f"Final score:        {player.score}", color_rgb(Color.CYAN), font=self._header_font)

        pygame.draw.line(self._screen, (85, 30, 30), (TOTAL_WIDTH // 4, 265), (TOTAL_WIDTH * 3 // 4, 265), 2)

        hs_x = (TOTAL_WIDTH - 440) // 2
        self._draw_text(hs_x, 290, "-- HIGH SCORE LEADERBOARD --", color_rgb(Color.YELLOW), font=self._header_font)
        
        curr_y = 330
        for rank, s in enumerate(highscores[:10], start=1):
            is_current = (s[0] == player.score and s[1] == player.max_depth and s[2] == player.kills)
            
            color = color_rgb(Color.CYAN) if is_current else color_rgb(Color.GRAY)
            marker = " *" if is_current else "  "
            
            txt = f"{rank:>2}.{marker}Score: {s[0]:>5}   Depth: {s[1]:>2}   Kills: {s[2]:>3}"
            self._draw_text(hs_x, curr_y, txt, color, font=self._ui_font)
            curr_y += 24

        exit_surf = self._header_font.render("Press ANY KEY to Return to Title Screen", True, color_rgb(Color.YELLOW))
        self._screen.blit(exit_surf, ((TOTAL_WIDTH - exit_surf.get_width()) // 2, 620))

        self._screen.blit(self._crt_surface, (0, 0))
        pygame.display.flip()
