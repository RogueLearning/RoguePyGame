import datetime
import os
import random
import sys
import pygame
from enum import Enum

from Entities.monster import Monster
from Entities.player import Player
from Items.item import Item, ItemKind
from Map import fov
from Map.dungeon_level import DungeonLevel
from Map.map_generator import MapGenerator
from Map.tile import TileType
from UI.colors import Color
from UI.keyboard import KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_UP
from UI.message_log import MessageLog
from UI.renderer import MAP_HEIGHT, MAP_WIDTH, Renderer

FOV_RADIUS = 8
HIGH_SCORE_FILE = "highscores.txt"


class GameState(Enum):
    TITLE_SCREEN = 1
    PLAYING = 2
    ANIMATING = 3
    INVENTORY = 4
    ZAP_PROMPT = 5
    GAME_OVER = 6


class Game:
    def __init__(self):
        self._rng = random.Random()
        
        # Initialize display in renderer
        self._renderer = Renderer()
        
        self._log = MessageLog()
        self._player = Player()
        self._levels: dict[int, DungeonLevel] = {}
        self._level: DungeonLevel | None = None
        self._quit = False
        self._boss_spawned = False
        
        self._state = GameState.TITLE_SCREEN
        self._clock = pygame.time.Clock()
        self._highscores = _load_scores()

    def run(self):
        self._enter_level(1, from_above=True)
        self._log.add(f"Welcome to the dungeon. Depth {self._player.depth}.", Color.YELLOW)

        while not self._quit:
            # 1. Process Event Dispatch
            self._handle_pygame_events()

            # 2. Render Screen Frame based on current game state
            if self._state == GameState.TITLE_SCREEN:
                self._renderer.render_title_screen(self._highscores)
            elif self._state == GameState.GAME_OVER:
                self._renderer.render_game_over(self._player, self._highscores)
            else:
                # PLAYING, ANIMATING, INVENTORY, ZAP_PROMPT
                fov.compute(self._level, self._player.x, self._player.y, FOV_RADIUS)
                show_inventory = (self._state == GameState.INVENTORY)
                self._renderer.render(self._level, self._player, self._log, show_inventory=show_inventory)

            # 3. Game Tick Clock (Locked to 60 FPS)
            self._clock.tick(60)

        pygame.quit()

    def _reset_game(self):
        self._player = Player()
        self._levels = {}
        self._level = None
        self._boss_spawned = False
        self._enter_level(1, from_above=True)
        self._log = MessageLog()
        self._log.add(f"Welcome to the dungeon. Depth {self._player.depth}.", Color.YELLOW)
        
        # Reset visual position arrays
        self._renderer._entity_positions = {}
        self._renderer._bumps = {}
        self._renderer._projectiles = []
        self._renderer._damage_texts = []
        self._renderer._particles = []

    def _handle_pygame_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit = True
                return
                
            elif event.type == pygame.KEYDOWN:
                # Quit key check for quick escape
                if event.key == pygame.K_q and self._state in (GameState.TITLE_SCREEN, GameState.PLAYING):
                    self._quit = True
                    return

                # Game State event dispatcher
                if self._state == GameState.TITLE_SCREEN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self._state = GameState.PLAYING
                        
                elif self._state == GameState.GAME_OVER:
                    # Press any key to return to title screen
                    self._state = GameState.TITLE_SCREEN
                    self._reset_game()
                    
                elif self._state == GameState.PLAYING:
                    # Don't accept movement keypresses if projectiles are in transit
                    if self._renderer.is_animating():
                        continue
                        
                    # Handle symbol characters directly using event.unicode for layout-safety
                    char = event.unicode
                    if char == ">":
                        key_str = ">"
                    elif char == "<":
                        key_str = "<"
                    elif event.key == pygame.K_SPACE:
                        took_turn = self._attack_in_facing_direction()
                        if not self._player.is_alive:
                            self._trigger_game_over()
                        elif took_turn and not self._renderer.is_animating():
                            self._monsters_act()
                            if not self._player.is_alive:
                                self._trigger_game_over()
                        continue
                    else:
                        key_str = self._map_key(event.key)

                    if key_str:
                        took_turn = self._handle_input(key_str)
                        if not self._player.is_alive:
                            self._trigger_game_over()
                        elif took_turn and not self._renderer.is_animating():
                            self._monsters_act()
                            if not self._player.is_alive:
                                self._trigger_game_over()
                                
                elif self._state == GameState.INVENTORY:
                    if event.key in (pygame.K_ESCAPE, pygame.K_i):
                        self._state = GameState.PLAYING
                    else:
                        char = event.unicode.lower()
                        if char and 'a' <= char <= 'z':
                            idx = ord(char) - ord('a')
                            items = self._player.inventory.items
                            if 0 <= idx < len(items):
                                self._use_item(items[idx])
                            self._state = GameState.PLAYING
                            
                elif self._state == GameState.ZAP_PROMPT:
                    dx, dy = 0, 0
                    if event.key in (pygame.K_UP, pygame.K_w):
                        dy = -1
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        dy = 1
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        dx = -1
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        dx = 1
                    else:
                        self._log.add("You hold the wand. Nothing happens.", Color.DARK_GRAY)
                        self._state = GameState.PLAYING
                        continue

                    self._start_lightning(dx, dy)

    def _map_key(self, key_val) -> str | None:
        if key_val in (pygame.K_UP, pygame.K_w):
            return KEY_UP
        if key_val in (pygame.K_DOWN, pygame.K_s):
            return KEY_DOWN
        if key_val in (pygame.K_LEFT, pygame.K_a):
            return KEY_LEFT
        if key_val in (pygame.K_RIGHT, pygame.K_d):
            return KEY_RIGHT
        if key_val == pygame.K_g:
            return "g"
        if key_val == pygame.K_i:
            return "i"
        if key_val == pygame.K_z:
            return "z"
        return None

    def _trigger_game_over(self):
        self._state = GameState.GAME_OVER
        entry = (self._player.score, self._player.max_depth, self._player.kills, datetime.datetime.now())
        self._highscores.append(entry)
        self._highscores.sort(key=lambda s: s[0], reverse=True)
        self._highscores = self._highscores[:10]
        _save_scores(self._highscores)

    def _enter_level(self, depth: int, from_above: bool):
        level = self._levels.get(depth)
        if level is None:
            gen = MapGenerator(self._rng)
            level = gen.generate(MAP_WIDTH, MAP_HEIGHT, depth, not self._boss_spawned)
            self._levels[depth] = level
            if any(m.is_boss for m in level.monsters):
                self._boss_spawned = True
                self._log.add("An ominous presence stalks this floor...", Color.DARK_RED)
        self._level = level
        self._player.depth = depth

        if depth > self._player.max_depth:
            self._player.max_depth = depth
            if depth > 1:
                heal = min(5, self._player.max_hp - self._player.hp)
                self._player.hp += heal

        if not from_above:
            spawn = self._level.stairs_down
        elif self._level.has_stairs_up:
            spawn = self._level.stairs_up
        else:
            spawn = self._level.player_spawn

        self._player.x, self._player.y = spawn
        self._player.update_appearance()

    def _handle_input(self, key: str) -> bool:
        if key == KEY_UP:
            return self._try_move(0, -1)
        if key == KEY_DOWN:
            return self._try_move(0, 1)
        if key == KEY_LEFT:
            return self._try_move(-1, 0)
        if key == KEY_RIGHT:
            return self._try_move(1, 0)
        lower = key.lower() if key else ""
        if lower == "g":
            return self._try_pick_up()
        if lower == "i":
            self._state = GameState.INVENTORY
            return False
        if key == ">":
            return self._try_descend()
        if key == "<":
            return self._try_ascend()
        if lower == "z":
            wand = self._player.inventory.equipped_wand
            if wand is None:
                self._log.add("You have no wand readied.", Color.DARK_GRAY)
                return False
            if wand.charges <= 0:
                self._log.add(f"The {wand.name} is spent.", Color.DARK_GRAY)
                return False
            self._log.add("Zap which direction? (arrow keys / WASD)", Color.MAGENTA)
            self._state = GameState.ZAP_PROMPT
            return False
        return False

    def _try_move(self, dx: int, dy: int) -> bool:
        # Update player facing direction
        if dx > 0:
            self._player.facing = "RIGHT"
        elif dx < 0:
            self._player.facing = "LEFT"
        elif dy > 0:
            self._player.facing = "DOWN"
        elif dy < 0:
            self._player.facing = "UP"

        nx = self._player.x + dx
        ny = self._player.y + dy
        monster = self._level.monster_at(nx, ny)
        if monster is not None:
            self._attack_monster(monster)
            return True
        if not self._level.is_walkable(nx, ny):
            return False

        self._player.x = nx
        self._player.y = ny


        self._try_use_fountain(nx, ny)

        here = self._level.item_at(nx, ny)
        if here is not None:
            self._log.add(f"You see a {here.item.display_name} here. (press g)", Color.CYAN)
        tile_type = self._level.tiles[nx][ny].type
        if tile_type == TileType.STAIRS_DOWN:
            self._log.add("Stairs lead down here. (press >)", Color.YELLOW)
        elif tile_type == TileType.STAIRS_UP:
            self._log.add("Stairs lead up here. (press <)", Color.YELLOW)
        return True

    def _try_use_fountain(self, x: int, y: int):
        if self._level.tiles[x][y].type != TileType.FOUNTAIN:
            return

        weapon = self._player.inventory.equipped_weapon
        if weapon is None:
            self._log.add("A fountain hums with magic, but you have no weapon equipped.", Color.YELLOW)
            return
        if weapon.is_enchanted:
            self._log.add(f"The fountain's power has already blessed your {weapon.display_name}.", Color.DARK_GRAY)
            return

        weapon.is_enchanted = True
        self._player.update_appearance()
        self._log.add(f"Your {weapon.display_name} glows with enchantment!", Color.CYAN)
        
        # Enchanter graphic visual flash
        self._renderer.add_particles(x, y, (240, 200, 30), count=20)
        self._renderer.add_damage_text(x, y, "BLESSED!", (240, 200, 30))

    def _attack_monster(self, m: Monster):
        weapon = self._player.inventory.equipped_weapon
        if m.is_boss and not (weapon is not None and weapon.is_enchanted):
            self._log.add(f"Your attack glances off the {m.name}. Only enchanted steel can harm it!", Color.YELLOW)
            self._renderer.add_bump(self._player, (m.x, m.y))
            self._renderer.add_damage_text(m.x, m.y, "GLANCE", (240, 200, 30))
            return

        dmg = max(1, self._player.attack + self._rng.randint(-1, 1))
        m.hp -= dmg
        self._log.add(f"You hit the {m.name} for {dmg}.", Color.WHITE)
        
        # Visual bumps, floating text numbers, and slice particles
        self._renderer.add_bump(self._player, (m.x, m.y))
        self._renderer.add_damage_text(m.x, m.y, f"-{dmg}", (220, 55, 55))
        self._renderer.add_particles(m.x, m.y, (180, 50, 50), count=8)

        if not m.is_alive:
            self._log.add(f"You kill the {m.name}!", Color.GREEN)
            self._player.kills += 1
            if m in self._level.monsters:
                self._level.monsters.remove(m)

    def _try_pick_up(self) -> bool:
        ie = self._level.item_at(self._player.x, self._player.y)
        if ie is None:
            self._log.add("Nothing to pick up.", Color.DARK_GRAY)
            return False
        if not self._player.inventory.add(ie.item):
            self._log.add("Your pack is full.", Color.RED)
            return False
        self._level.items.remove(ie)
        self._log.add(f"You pick up the {ie.item.display_name}.", Color.CYAN)
        
        # Graphic pop item grab effects
        self._renderer.add_damage_text(self._player.x, self._player.y, "GET!", (45, 175, 205))
        self._renderer.add_particles(self._player.x, self._player.y, (45, 175, 205), count=6)
        return True

    def _use_item(self, item: Item):
        if item.kind == ItemKind.HEALING_POTION:
            healed = min(item.heal_amount, self._player.max_hp - self._player.hp)
            self._player.hp += healed
            if healed > 0:
                self._log.add(f"You drink the {item.display_name}. (+{healed} HP)", Color.GREEN)
                self._renderer.add_damage_text(self._player.x, self._player.y, f"+{healed} HP", (46, 196, 120))
                self._renderer.add_particles(self._player.x, self._player.y, (50, 220, 100), count=10)
            else:
                self._log.add(f"You drink the {item.display_name}. No effect.", Color.GREEN)
            self._player.inventory.remove(item)
            self._player.update_appearance()
        elif item.kind == ItemKind.WEAPON:
            self._player.inventory.equipped_weapon = item
            self._player.update_appearance()
            self._log.add(f"You equip the {item.display_name}.", Color.CYAN)
            self._renderer.add_damage_text(self._player.x, self._player.y, "EQUIP", (45, 175, 205))
        elif item.kind == ItemKind.WAND:
            self._player.inventory.equipped_wand = item
            self._log.add(f"You ready the {item.display_name}.", Color.MAGENTA)
            self._renderer.add_damage_text(self._player.x, self._player.y, "READY", (200, 60, 200))

    def _try_descend(self) -> bool:
        if self._level.tiles[self._player.x][self._player.y].type != TileType.STAIRS_DOWN:
            self._log.add("No stairs down here.", Color.DARK_GRAY)
            return False
        self._enter_level(self._player.depth + 1, from_above=True)
        self._log.add(f"You descend to depth {self._player.depth}.", Color.YELLOW)
        
        # Magic stairs transition flash
        self._renderer.trigger_shake(8.0)
        self._renderer.add_particles(self._player.x, self._player.y, (240, 205, 35), count=15)
        return True

    def _attack_in_facing_direction(self) -> bool:
        facing = self._player.facing
        dx, dy = 0, 0
        if facing == "UP":
            dy = -1
        elif facing == "DOWN":
            dy = 1
        elif facing == "LEFT":
            dx = -1
        elif facing == "RIGHT":
            dx = 1

        # Check if wand is equipped and has charges. If so, zap lightning!
        wand = self._player.inventory.equipped_wand
        if wand is not None and wand.charges > 0:
            self._start_lightning(dx, dy)
            return True

        # Melee attack
        nx = self._player.x + dx
        ny = self._player.y + dy

        monster = self._level.monster_at(nx, ny)
        if monster is not None:
            self._attack_monster(monster)
            return True

        # Swing in air (visually bump and show message)
        self._renderer.add_bump(self._player, (nx, ny))
        self._log.add("You swing at thin air.", Color.DARK_GRAY)
        return True

    def _start_lightning(self, dx: int, dy: int):
        wand = self._player.inventory.equipped_wand
        if wand is None or wand.charges <= 0:
            self._state = GameState.PLAYING
            return

        x, y = self._player.x, self._player.y
        path = []
        target_monster = None
        target_wall = False

        for _ in range(wand.wand_range):
            x += dx
            y += dy
            if not self._level.in_bounds(x, y):
                break
            path.append((x, y))
            if not self._level.tiles[x][y].is_walkable:
                target_wall = True
                break
            m = self._level.monster_at(x, y)
            if m is not None:
                target_monster = m
                break

        if not path:
            self._log.add("The lightning fizzles instantly.", Color.DARK_GRAY)
            self._state = GameState.PLAYING
            return

        wand.charges -= 1
        self._state = GameState.ANIMATING

        # Projectile callback runs when the lightning visual hits target
        def on_projectile_complete():
            nonlocal target_monster, target_wall
            if target_wall:
                self._log.add("The lightning crackles against the wall.", Color.RED)
            elif target_monster is not None:
                m = target_monster
                dmg = wand.wand_damage + self._rng.randint(-1, 1)
                m.hp -= dmg
                self._log.add(f"The lightning shocks the {m.name} for {dmg}!", Color.CYAN)
                
                # Floating damage text and sparks
                self._renderer.add_damage_text(m.x, m.y, f"-{dmg}", (50, 190, 220))
                self._renderer.add_particles(m.x, m.y, (100, 200, 255), count=12)

                if not m.is_alive:
                    self._log.add(f"You shock the {m.name} to dust!", Color.GREEN)
                    self._player.kills += 1
                    if m in self._level.monsters:
                        self._level.monsters.remove(m)
            else:
                self._log.add("The lightning dissipates into the dark.", Color.DARK_GRAY)

            # Monsters act after player turn is complete
            if self._player.is_alive:
                self._monsters_act()
                if not self._player.is_alive:
                    self._trigger_game_over()
                else:
                    self._state = GameState.PLAYING
            else:
                self._trigger_game_over()

        # Launch the lightning projectile animation on the renderer (type="lightning")
        self._renderer.add_projectile(path, on_projectile_complete, type="lightning")

    def _try_ascend(self) -> bool:
        if self._level.tiles[self._player.x][self._player.y].type != TileType.STAIRS_UP:
            self._log.add("No stairs up here.", Color.DARK_GRAY)
            return False
        if self._player.depth <= 1:
            self._log.add("You cannot leave the dungeon yet.", Color.YELLOW)
            return False
        self._enter_level(self._player.depth - 1, from_above=False)
        self._log.add(f"You ascend to depth {self._player.depth}.", Color.YELLOW)
        
        # Ascent particle flash
        self._renderer.trigger_shake(8.0)
        self._renderer.add_particles(self._player.x, self._player.y, (245, 245, 245), count=15)
        return True

    def _monsters_act(self):
        for m in list(self._level.monsters):
            if not m.is_alive:
                continue
            if not self._level.tiles[m.x][m.y].visible:
                continue

            dx = self._player.x - m.x
            dy = self._player.y - m.y

            if abs(dx) + abs(dy) == 1:
                dmg = max(1, m.attack + self._rng.randint(-1, 1))
                self._player.hp -= dmg
                self._log.add(f"The {m.name} hits you for {dmg}.", Color.RED)
                
                # Animations
                self._renderer.add_bump(m, (self._player.x, self._player.y))
                self._renderer.add_damage_text(self._player.x, self._player.y, f"-{dmg}", (220, 55, 55))
                self._renderer.add_particles(self._player.x, self._player.y, (210, 50, 50), count=8)
                self._renderer.trigger_shake(6.0)

                if not self._player.is_alive:
                    self._log.add(f"The {m.name} kills you...", Color.RED)
                    return
                continue

            sx = (dx > 0) - (dx < 0)
            sy = (dy > 0) - (dy < 0)
            prefer_x = abs(dx) >= abs(dy)
            if prefer_x:
                if sx != 0 and self._try_step_monster(m, sx, 0):
                    continue
                if sy != 0:
                    self._try_step_monster(m, 0, sy)
            else:
                if sy != 0 and self._try_step_monster(m, 0, sy):
                    continue
                if sx != 0:
                    self._try_step_monster(m, sx, 0)

    def _try_step_monster(self, m: Monster, dx: int, dy: int) -> bool:
        nx = m.x + dx
        ny = m.y + dy
        if not self._level.is_walkable(nx, ny):
            return False
        if self._level.monster_at(nx, ny) is not None:
            return False
        if nx == self._player.x and ny == self._player.y:
            return False
        m.x = nx
        m.y = ny
        return True


def _load_scores() -> list[tuple[int, int, int, datetime.datetime]]:
    result: list[tuple[int, int, int, datetime.datetime]] = []
    if not os.path.exists(HIGH_SCORE_FILE):
        return result
    with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) != 4:
                continue
            try:
                s = int(parts[0])
                d = int(parts[1])
                k = int(parts[2])
                dt = datetime.datetime.fromisoformat(parts[3])
            except ValueError:
                continue
            result.append((s, d, k, dt))
    return result


def _save_scores(scores: list[tuple[int, int, int, datetime.datetime]]):
    with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as f:
        for s in scores:
            f.write(f"{s[0]}|{s[1]}|{s[2]}|{s[3].isoformat()}\n")
