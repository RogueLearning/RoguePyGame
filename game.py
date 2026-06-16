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
from Map.map_generator import MapGenerator, DUNGEON_DEPTH
from Map.tile import TileType
from UI.colors import Color
from UI.keyboard import KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_UP
from UI.message_log import MessageLog
from UI.renderer import MAP_HEIGHT, MAP_WIDTH, Renderer
from UI.sound import SoundManager
import save_system

FOV_RADIUS = 8
HIGH_SCORE_FILE = "highscores.txt"
MONSTER_ACT_COOLDOWN = 35  # Frames between monster steps in real-time


class GameState(Enum):
    TITLE_SCREEN = 1
    PLAYING = 2
    ANIMATING = 3
    INVENTORY = 4
    ZAP_PROMPT = 5
    GAME_OVER = 6
    SHOP = 7
    CLASS_SELECT = 8
    CAMPAIGN_SELECT = 9
    GRAPPLE_PROMPT = 10
    VICTORY = 11


class Game:
    def __init__(self):
        self._rng = random.Random()
        self._renderer = Renderer()
        
        self._log = MessageLog()
        self._player = Player()
        self._levels: dict[tuple[str, int], DungeonLevel] = {}
        self._level: DungeonLevel | None = None
        self._overworld: DungeonLevel | None = None
        self._in_overworld = True
        self._current_dungeon_id = ""
        self._quit = False
        self._boss_spawned = False
        
        self._state = GameState.TITLE_SCREEN
        self._clock = pygame.time.Clock()
        self._highscores = _load_scores()
        self._active_merchant = None
        self._selected_class_idx = 0
        self._active_campaign = None       # slot 1-3 this session writes to
        self._selected_campaign_idx = 0    # cursor on the campaign-select screen
        self._sound = SoundManager()

        # Real-time update variables
        self._move_cooldown = 0
        self._attack_cooldown = 0
        self._monster_timer = MONSTER_ACT_COOLDOWN

    def run(self):
        # Clear and generate overworld at startup
        self._levels = {}
        self._boss_spawned = False
        self._in_overworld = True
        self._current_dungeon_id = ""
        gen = MapGenerator(self._rng)
        self._overworld = gen.generate_overworld()
        self._level = self._overworld
        self._player.x, self._player.y = self._overworld.player_spawn
        self._player.depth = 0
        self._log.add("Welcome to Rogue PyGame!", Color.YELLOW)

        while not self._quit:
            # 1. Dispatch discrete events (like menus, quit, click triggers)
            self._handle_pygame_events()

            # 2. Update real-time gameplay cycles if actively playing
            if self._state == GameState.PLAYING:
                # Decrement cooldown counts
                if self._move_cooldown > 0:
                    self._move_cooldown -= 1
                if self._attack_cooldown > 0:
                    self._attack_cooldown -= 1
                    
                # Wizard Wand Recharge Tick
                if getattr(self._player, "char_class", "") == "Wizard":
                    if not hasattr(self, "_wizard_recharge_timer"):
                        self._wizard_recharge_timer = 300
                    self._wizard_recharge_timer -= 1
                    if self._wizard_recharge_timer <= 0:
                        self._wizard_recharge_timer = 300
                        wand = self._player.inventory.equipped_wand
                        if wand is not None and wand.kind == ItemKind.WAND:
                            if wand.charges < 3:
                                wand.charges += 1
                                self._log.add("Your wand sparkles as it recharges a charge.", Color.MAGENTA)
                                self._renderer.add_particles(self._player.x, self._player.y, (100, 200, 255), count=6)

                # Process held inputs (movements/attacks)
                if not self._renderer.is_animating():
                    self._handle_continuous_input()

                # Process monster behavior timers
                self._monster_timer -= 1
                if self._monster_timer <= 0:
                    self._monsters_act()
                    self._monster_timer = MONSTER_ACT_COOLDOWN
                    if not self._player.is_alive:
                        self._trigger_game_over()

                # Update fire mechanics (burning tiles and burning statuses)
                if self._level is not None:
                    # Update ground fire timers
                    for pos in list(self._level.burning_tiles.keys()):
                        self._level.burning_tiles[pos] -= 1
                        if self._level.burning_tiles[pos] <= 0:
                            del self._level.burning_tiles[pos]

                    # Standing on a burning tile catches fire
                    if (self._player.x, self._player.y) in self._level.burning_tiles:
                        if getattr(self._player, "burning_timer", 0) < 180:
                            self._player.burning_timer = 180
                    for m in self._level.monsters:
                        if m.is_alive and not getattr(m, "is_npc", False):
                            if (m.x, m.y) in self._level.burning_tiles:
                                if getattr(m, "burning_timer", 0) < 180:
                                    m.burning_timer = 180

                    # Ticking damage for burning player
                    if self._player.is_alive and getattr(self._player, "burning_timer", 0) > 0:
                        self._player.burning_timer -= 1
                        if self._player.burning_timer % 30 == 0:
                            self._player.hp -= 1
                            self._sound.play("hit")
                            self._renderer.add_damage_text(self._player.x, self._player.y, "-1 Fire", (255, 80, 0))
                            self._renderer.add_particles(self._player.x, self._player.y, (255, 100, 0), count=4)
                            self._log.add("You are burning!", Color.RED)
                            if not self._player.is_alive:
                                self._log.add("You burned to death...", Color.RED)
                                self._trigger_game_over()

                    # Ticking damage for burning monsters
                    for m in list(self._level.monsters):
                        if m.is_alive and getattr(m, "burning_timer", 0) > 0:
                            m.burning_timer -= 1
                            if m.burning_timer % 30 == 0:
                                if not getattr(m, "is_npc", False):
                                    m.hp -= 1
                                    self._renderer.add_damage_text(m.x, m.y, "-1 Fire", (255, 80, 0))
                                    self._renderer.add_particles(m.x, m.y, (255, 100, 0), count=4)
                                    if not m.is_alive:
                                        self._log.add(f"The {m.name} burns to death!", Color.GREEN)
                                        self._player.kills += 1
                                        if m in self._level.monsters:
                                            self._level.monsters.remove(m)
                                        self._drop_monster_loot(m)

            # 3. Render frame view
            if self._state == GameState.TITLE_SCREEN:
                self._renderer.render_title_screen(self._highscores)
            elif self._state == GameState.CAMPAIGN_SELECT:
                self._renderer.render_campaign_select(save_system.list_campaigns(), self._selected_campaign_idx)
            elif self._state == GameState.CLASS_SELECT:
                self._renderer.render_class_select(self._selected_class_idx)
            elif self._state == GameState.GAME_OVER:
                self._renderer.render_game_over(self._player, self._highscores)
            elif self._state == GameState.VICTORY:
                self._renderer.render_victory(self._player)
            else:
                # PLAYING, ANIMATING, INVENTORY, ZAP_PROMPT, SHOP
                fov.compute(self._level, self._player.x, self._player.y, FOV_RADIUS)
                show_inventory = (self._state == GameState.INVENTORY)
                show_shop = self._active_merchant if (self._state == GameState.SHOP) else None
                self._renderer.render(self._level, self._player, self._log, show_inventory=show_inventory, show_shop=show_shop)

            # 4. Clock Tick
            self._clock.tick(60)

        pygame.quit()

    def _reset_game(self):
        self._player = Player()
        self._levels = {}
        self._boss_spawned = False
        self._in_overworld = True
        self._current_dungeon_id = ""
        gen = MapGenerator(self._rng)
        self._overworld = gen.generate_overworld()
        self._level = self._overworld
        self._player.x, self._player.y = self._overworld.player_spawn
        self._player.depth = 0
        self._log = MessageLog()
        self._log.add("Welcome to the Overworld.", Color.YELLOW)
        self._log.add("Explore the quadrants, talk to NPCs, and find a dungeon portal [Enter].", Color.GREEN)
        self._active_merchant = None
        self._selected_class_idx = 0
        
        # Reset visual position arrays
        self._renderer._entity_positions = {}
        self._renderer._bumps = {}
        self._renderer._projectiles = []
        self._renderer._damage_texts = []
        self._renderer._particles = []

        # Reset real-time values
        self._move_cooldown = 0
        self._attack_cooldown = 0
        self._monster_timer = MONSTER_ACT_COOLDOWN

    def _select_class_and_start(self, class_name: str):
        self._player = Player()
        self._player.char_class = class_name
        
        # Apply class-specific attributes
        if class_name == "Knight":
            self._player.hp = 40
            self._player.max_hp = 40
            self._player.base_attack = 4
            
            # Add shortsword
            sword = Item()
            sword.name = "shortsword"
            sword.glyph = "🗡️"
            sword.color = Color.CYAN
            sword.kind = ItemKind.WEAPON
            sword.attack_bonus = 2
            self._player.inventory.add(sword)
            self._player.inventory.equipped_weapon = sword
            
        elif class_name == "Wizard":
            self._player.hp = 20
            self._player.max_hp = 20
            self._player.base_attack = 3
            
            # Add wand of lightning
            wand = Item()
            wand.name = "wand of lightning"
            wand.glyph = "🪄"
            wand.color = Color.CYAN
            wand.kind = ItemKind.WAND
            wand.wand_damage = 8
            wand.wand_range = 6
            wand.charges = 3
            wand.max_charges = 3
            self._player.inventory.add(wand)
            self._player.inventory.equipped_wand = wand
            
        elif class_name == "Rogue":
            self._player.hp = 30
            self._player.max_hp = 30
            self._player.base_attack = 4
            self._player.arrows = 15
            
            # Add dagger
            dagger = Item()
            dagger.name = "dagger"
            dagger.glyph = "🗡️"
            dagger.color = Color.CYAN
            dagger.kind = ItemKind.WEAPON
            dagger.attack_bonus = 1
            self._player.inventory.add(dagger)
            
            # Add bow
            bow = Item()
            bow.name = "bow"
            bow.glyph = "🏹"
            bow.color = Color.CYAN
            bow.kind = ItemKind.WEAPON
            bow.attack_bonus = 2
            self._player.inventory.add(bow)
            self._player.inventory.equipped_weapon = bow

        # Clear and generate overworld
        self._levels = {}
        self._boss_spawned = False
        self._in_overworld = True
        self._current_dungeon_id = ""
        gen = MapGenerator(self._rng)
        self._overworld = gen.generate_overworld()
        self._level = self._overworld
        self._player.x, self._player.y = self._overworld.player_spawn
        self._player.depth = 0
        self._log = MessageLog()
        self._log.add(f"Welcome, {class_name}! You are in the Overworld.", Color.YELLOW)
        self._log.add("Explore the quadrants, talk to NPCs, and find a dungeon portal [Enter].", Color.GREEN)
        self._active_merchant = None
        
        # Reset visual position arrays
        self._renderer._entity_positions = {}
        self._renderer._bumps = {}
        self._renderer._projectiles = []
        self._renderer._damage_texts = []
        self._renderer._particles = []

        # Reset real-time values
        self._move_cooldown = 0
        self._attack_cooldown = 0
        self._monster_timer = MONSTER_ACT_COOLDOWN
        self._wizard_recharge_timer = 300

        self._state = GameState.PLAYING

        # Establish the campaign's first save point immediately.
        if self._active_campaign is not None:
            try:
                save_system.save_campaign(self, self._active_campaign)
            except Exception:
                pass

    def _handle_campaign_select_key(self, event):
        metas = save_system.list_campaigns()
        n = save_system.NUM_CAMPAIGNS

        if event.key in (pygame.K_ESCAPE,):
            self._state = GameState.TITLE_SCREEN
            return
        if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
            self._selected_campaign_idx = (self._selected_campaign_idx - 1) % n
            return
        if event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
            self._selected_campaign_idx = (self._selected_campaign_idx + 1) % n
            return
        if event.key in (pygame.K_x, pygame.K_DELETE, pygame.K_BACKSPACE):
            # Erase the highlighted campaign so the slot can be reused.
            slot = self._selected_campaign_idx + 1
            if metas[self._selected_campaign_idx] is not None:
                save_system.delete_campaign(slot)
            return

        # Number keys jump straight to a slot.
        if event.unicode in ("1", "2", "3"):
            self._selected_campaign_idx = int(event.unicode) - 1

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) or event.unicode in ("1", "2", "3"):
            slot = self._selected_campaign_idx + 1
            if metas[self._selected_campaign_idx] is not None:
                self._load_campaign_and_play(slot)
            else:
                # Empty slot -> create a fresh hero here.
                self._active_campaign = slot
                self._selected_class_idx = 0
                self._state = GameState.CLASS_SELECT

    def _save_current_campaign(self):
        if self._active_campaign is None:
            self._active_campaign = 1
        try:
            save_system.save_campaign(self, self._active_campaign)
            self._log.add(f"Campaign {self._active_campaign} saved.", Color.GREEN)
            self._renderer.add_damage_text(self._player.x, self._player.y, "SAVED", (46, 196, 120))
            self._sound.play("pickup")
        except Exception:
            self._log.add("Save failed.", Color.RED)

    def _load_campaign_and_play(self, slot: int) -> bool:
        if not save_system.load_campaign(self, slot):
            return False
        self._active_campaign = slot
        self._active_merchant = None

        # Clear stale animation/interpolation state from the prior view.
        self._renderer._entity_positions = {}
        self._renderer._bumps = {}
        self._renderer._projectiles = []
        self._renderer._damage_texts = []
        self._renderer._particles = []

        self._move_cooldown = 0
        self._attack_cooldown = 0
        self._monster_timer = MONSTER_ACT_COOLDOWN
        self._wizard_recharge_timer = 300

        self._state = GameState.PLAYING
        self._log.add(f"Campaign {slot} loaded. Welcome back, {self._player.char_class}!", Color.YELLOW)
        return True

    def _handle_pygame_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit = True
                return
                
            elif event.type == pygame.KEYDOWN:
                # Quick quit key
                if event.key == pygame.K_q and self._state in (GameState.TITLE_SCREEN, GameState.PLAYING):
                    self._quit = True
                    return

                if self._state == GameState.TITLE_SCREEN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self._state = GameState.CAMPAIGN_SELECT
                        self._selected_campaign_idx = 0

                elif self._state == GameState.CAMPAIGN_SELECT:
                    self._handle_campaign_select_key(event)

                elif self._state == GameState.CLASS_SELECT:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self._state = GameState.CAMPAIGN_SELECT
                    elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
                        self._selected_class_idx = (self._selected_class_idx - 1) % 3
                    elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
                        self._selected_class_idx = (self._selected_class_idx + 1) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        classes = ["Knight", "Wizard", "Rogue"]
                        self._select_class_and_start(classes[self._selected_class_idx])
                    else:
                        char = event.unicode.lower()
                        if char in ("1", "k"):
                            self._select_class_and_start("Knight")
                        elif char in ("2", "w"):
                            self._select_class_and_start("Wizard")
                        elif char in ("3", "r"):
                            self._select_class_and_start("Rogue")
                        
                elif self._state in (GameState.GAME_OVER, GameState.VICTORY):
                    self._state = GameState.TITLE_SCREEN
                    self._reset_game()

                elif self._state == GameState.PLAYING:
                    if self._renderer.is_animating():
                        continue

                    # Quick-save the active campaign
                    if event.key == pygame.K_F5:
                        self._save_current_campaign()
                        continue

                    # Handle Enter key for stairs
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        current_tile = self._level.tiles[self._player.x][self._player.y].type
                        if current_tile == TileType.STAIRS_DOWN:
                            self._try_descend()
                        elif current_tile == TileType.STAIRS_UP:
                            self._try_ascend()
                        continue

                    # Handle symbol triggers (discrete events)
                    char = event.unicode
                    if char == ">":
                        self._try_descend()
                    elif char == "<":
                        self._try_ascend()
                    else:
                        key_str = self._map_key(event.key)
                        # Discrete gameplay hotkeys (pickup, inventory, zap, grapple)
                        if key_str in ("g", "i", "z", "h"):
                            self._handle_input(key_str)
                                
                elif self._state == GameState.INVENTORY:
                    if event.key in (pygame.K_ESCAPE, pygame.K_i):
                        self._state = GameState.PLAYING
                    else:
                        char = event.unicode
                        if char and char.lower().isalpha() and 'a' <= char.lower() <= 'z':
                            idx = ord(char.lower()) - ord('a')
                            items = self._player.inventory.items
                            if 0 <= idx < len(items):
                                if char.isupper():
                                    self._drop_item(items[idx])  # Shift+letter = drop
                                else:
                                    self._use_item(items[idx])   # letter = use/equip/unequip
                            # Stay in the inventory so several items can be
                            # managed in one visit; ESC / I closes it.
                            
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

                elif self._state == GameState.GRAPPLE_PROMPT:
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
                        self._log.add("You coil the rope back up.", Color.DARK_GRAY)
                        self._state = GameState.PLAYING
                        continue
                    self._start_grapple(dx, dy)

                elif self._state == GameState.SHOP:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self._state = GameState.PLAYING
                        self._active_merchant = None
                    else:
                        char = event.unicode.lower()
                        slot_idx = -1
                        if char in ("1", "a"):
                            slot_idx = 0
                        elif char in ("2", "b"):
                            slot_idx = 1
                        elif char in ("3", "c"):
                            slot_idx = 2
                        elif char in ("4", "d"):
                            slot_idx = 3
                            
                        if 0 <= slot_idx < 4:
                            self._buy_shop_item(slot_idx)

    def _handle_continuous_input(self):
        keys = pygame.key.get_pressed()

        # Spacebar Attack Check (Ranged lightning or Melee swing)
        if keys[pygame.K_SPACE] and self._attack_cooldown == 0:
            self._attack_in_facing_direction()
            self._attack_cooldown = 15  # 250ms attack rate limit
            if not self._player.is_alive:
                self._trigger_game_over()
            return

        # Player Movement Key Holding Check
        if self._move_cooldown == 0:
            dx, dy = 0, 0
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1
            elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1

            if dx != 0 or dy != 0:
                took_turn = self._try_move(dx, dy)
                if took_turn:
                    # Check if we triggered an attack (cooldown is longer)
                    nx = self._player.x + dx
                    ny = self._player.y + dy
                    # If there was a monster, it was an attack, so give more visual impact frame lock
                    if self._level.monster_at(nx, ny) is not None:
                        self._move_cooldown = 15
                    else:
                        self._move_cooldown = 6 if getattr(self._player, "char_class", "") == "Rogue" else 8  # ~130ms walk cycle rate
                    if not self._player.is_alive:
                        self._trigger_game_over()

    def _map_key(self, key_val) -> str | None:
        if key_val == pygame.K_g:
            return "g"
        if key_val == pygame.K_i:
            return "i"
        if key_val == pygame.K_z:
            return "z"
        if key_val == pygame.K_h:
            return "h"
        return None

    def _trigger_game_over(self):
        self._state = GameState.GAME_OVER
        self._sound.play("death")
        entry = (self._player.score, self._player.max_depth, self._player.kills, datetime.datetime.now())
        self._highscores.append(entry)
        self._highscores.sort(key=lambda s: s[0], reverse=True)
        self._highscores = self._highscores[:10]
        _save_scores(self._highscores)

    def _trigger_victory(self):
        self._state = GameState.VICTORY
        self._sound.play("bless")
        self._renderer.trigger_flash(180, (255, 230, 140))
        self._log.add("With all three relics, the realm is saved!", Color.YELLOW)
        # A completed run scores a big bonus; record it on the leaderboard.
        bonus_score = self._player.score + 1000
        entry = (bonus_score, self._player.max_depth, self._player.kills, datetime.datetime.now())
        self._highscores.append(entry)
        self._highscores.sort(key=lambda s: s[0], reverse=True)
        self._highscores = self._highscores[:10]
        _save_scores(self._highscores)
        # Erase the campaign save -- this run is complete.
        if self._active_campaign is not None:
            save_system.delete_campaign(self._active_campaign)

    def _enter_level(self, dungeon_id: str, depth: int, from_above: bool):
        # Transition to Overworld
        if depth == 0:
            self._in_overworld = True
            self._level = self._overworld
            self._player.depth = 0
            
            # Spawn back on the dungeon entrance the player ascended from
            if self._current_dungeon_id == "crypt":
                spawn = self._overworld.stairs_down_crypt
            elif self._current_dungeon_id == "cellar":
                spawn = self._overworld.stairs_down_cellar
            elif self._current_dungeon_id == "cave":
                spawn = self._overworld.stairs_down_cave
            else:
                spawn = self._overworld.player_spawn
                
            self._player.x, self._player.y = spawn
            self._player.update_appearance()
            self._current_dungeon_id = ""
            return

        # Transition to a Dungeon
        self._in_overworld = False
        self._current_dungeon_id = dungeon_id
        
        level = self._levels.get((dungeon_id, depth))
        if level is None:
            gen = MapGenerator(self._rng)
            level = gen.generate(MAP_WIDTH, MAP_HEIGHT, depth, not self._boss_spawned,
                                 dungeon_id=dungeon_id)
            self._levels[(dungeon_id, depth)] = level
            if any(m.is_boss for m in level.monsters):
                self._boss_spawned = True
                self._log.add("The lair of a great beast! Slay it to claim its relic.", Color.DARK_RED)
                
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
        lower = key.lower() if key else ""
        if lower == "g":
            return self._try_pick_up()
        if lower == "i":
            self._state = GameState.INVENTORY
            return False
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
        if lower == "h":
            has_hook = any(it.kind == ItemKind.TOOL and it.name == "grappling hook"
                           for it in self._player.inventory.items)
            if not has_hook:
                self._log.add("You have no grappling hook.", Color.DARK_GRAY)
                return False
            self._log.add("Grapple which direction? (arrow keys / WASD)", Color.CYAN)
            self._state = GameState.GRAPPLE_PROMPT
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
            if getattr(monster, "is_merchant", False):
                self._active_merchant = monster
                self._state = GameState.SHOP
            elif getattr(monster, "is_chest", False):
                self._interact_with_chest(monster)
            elif getattr(monster, "is_npc", False):
                self._interact_with_npc(monster)
            else:
                self._attack_monster(monster)
            return True
        if not self._level.is_walkable(nx, ny):
            return False

        self._player.x = nx
        self._player.y = ny

        # Auto-pickup coins and arrows
        ie = self._level.item_at(nx, ny)
        if ie is not None and ie.item.kind.value == "coin":
            self._player.coins += ie.item.coin_value
            self._log.add(f"You find {ie.item.coin_value} gold coins!", Color.YELLOW)
            self._renderer.add_damage_text(self._player.x, self._player.y, f"+{ie.item.coin_value} Gold", (240, 200, 30))
            self._renderer.add_particles(self._player.x, self._player.y, (240, 200, 30), count=6)
            if ie in self._level.items:
                self._level.items.remove(ie)
            self._sound.play("pickup")
        elif ie is not None and ie.item.kind == ItemKind.ARROW:
            self._player.arrows = getattr(self._player, "arrows", 0) + ie.item.charges
            self._log.add(f"You pick up {ie.item.charges} arrows.", Color.CYAN)
            self._renderer.add_damage_text(self._player.x, self._player.y, f"+{ie.item.charges} Arrows", (200, 200, 200))
            self._renderer.add_particles(self._player.x, self._player.y, (220, 220, 220), count=6)
            if ie in self._level.items:
                self._level.items.remove(ie)
            self._sound.play("pickup")
        else:
            self._sound.play("walk")

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
        self._sound.play("bless")
        
        # Enchanter graphic visual flash
        self._renderer.add_particles(x, y, (240, 200, 30), count=20)
        self._renderer.add_damage_text(x, y, "BLESSED!", (240, 200, 30))

    def _attack_monster(self, m: Monster):
        if getattr(m, "is_npc", False):
            self._interact_with_npc(m)
            return

        weapon = self._player.inventory.equipped_weapon
        is_enchanted = weapon is not None and getattr(weapon, "is_enchanted", False)
        slash_color = (255, 215, 0) if is_enchanted else (150, 220, 255)
        self._renderer.add_slash(m.x, m.y, self._player.facing, slash_color)

        if m.is_boss and not (weapon is not None and weapon.is_enchanted):
            self._log.add(f"Your attack glances off the {m.name}. Only enchanted steel can harm it!", Color.YELLOW)
            self._renderer.add_bump(self._player, (m.x, m.y))
            self._renderer.add_damage_text(m.x, m.y, "GLANCE", (240, 200, 30))
            return

        is_crit = False
        if getattr(self._player, "char_class", "") == "Rogue" and self._rng.random() < 0.30:
            is_crit = True
            
        dmg = max(1, self._player.attack + self._rng.randint(-1, 1))
        if is_crit:
            dmg *= 2
            
        m.hp -= dmg
        self._sound.play("hit")
        self._renderer.add_bump(self._player, (m.x, m.y))
        
        if is_crit:
            self._log.add(f"Critical strike! You hit the {m.name} for {dmg}!", Color.YELLOW)
            self._renderer.add_damage_text(m.x, m.y, f"CRIT! -{dmg}", (255, 215, 0))
            self._renderer.add_particles(m.x, m.y, (255, 215, 0), count=15)
        else:
            self._log.add(f"You hit the {m.name} for {dmg}.", Color.WHITE)
            self._renderer.add_damage_text(m.x, m.y, f"-{dmg}", (220, 55, 55))
            self._renderer.add_particles(m.x, m.y, (180, 50, 50), count=8)

        # Sword of flames burning effect
        if weapon is not None and weapon.name == "sword of flames":
            if not getattr(m, "is_npc", False):
                m.burning_timer = 300  # 5 seconds
                self._log.add(f"Your sword of flames sets the {m.name} on fire!", Color.RED)
                self._renderer.add_particles(m.x, m.y, (255, 120, 20), count=6)

        if not m.is_alive:
            self._log.add(f"You kill the {m.name}!", Color.GREEN)
            self._player.kills += 1
            if m in self._level.monsters:
                self._level.monsters.remove(m)
            self._drop_monster_loot(m)

    def _drop_monster_loot(self, m: Monster):
        # A dungeon boss leaves behind its relic on death.
        artifact = getattr(m, "artifact", None)
        if artifact:
            from Items.item import create_artifact
            ax, ay = m.x, m.y
            if self._level.item_at(ax, ay) is not None:
                ax, ay = self._find_vacant_neighbor(m.x, m.y)
            self._level.items.append(create_artifact(artifact, ax, ay))
            self._log.add(f"The {m.name} falls! The {artifact} glimmers in the rubble.", Color.YELLOW)
            self._renderer.add_particles(ax, ay, (255, 215, 0), count=24)
            self._renderer.trigger_flash(120, (255, 230, 120))
            self._sound.play("bless")

        # Boss always drops a massive heap of coins!
        # Normal monsters drop coins with a 40% probability.
        chance = 1.0 if m.is_boss else 0.40
        if self._rng.random() < chance:
            if m.is_boss:
                value = self._rng.randint(25, 50) + 50
            else:
                value = self._rng.randint(2, 6) + self._player.depth * 2
            
            from Items.item import create_coin
            coin_entity = create_coin(m.x, m.y, value)
            self._level.items.append(coin_entity)
            self._log.add(f"The {m.name} dropped some gold coins.", Color.DARK_GRAY)

    def _try_pick_up(self) -> bool:
        ie = self._level.item_at(self._player.x, self._player.y)
        if ie is None:
            self._log.add("Nothing to pick up.", Color.DARK_GRAY)
            return False
        if ie.item.kind.value == "coin":
            self._player.coins += ie.item.coin_value
            self._log.add(f"You find {ie.item.coin_value} gold coins!", Color.YELLOW)
            self._renderer.add_damage_text(self._player.x, self._player.y, f"+{ie.item.coin_value} Gold", (240, 200, 30))
            self._renderer.add_particles(self._player.x, self._player.y, (240, 200, 30), count=6)
            if ie in self._level.items:
                self._level.items.remove(ie)
            self._sound.play("pickup")
            return True
        if ie.item.kind == ItemKind.ARROW:
            self._player.arrows = getattr(self._player, "arrows", 0) + ie.item.charges
            self._log.add(f"You pick up {ie.item.charges} arrows.", Color.CYAN)
            self._renderer.add_damage_text(self._player.x, self._player.y, f"+{ie.item.charges} Arrows", (200, 200, 200))
            self._renderer.add_particles(self._player.x, self._player.y, (220, 220, 220), count=6)
            if ie in self._level.items:
                self._level.items.remove(ie)
            self._sound.play("pickup")
            return True
        if ie.item.kind == ItemKind.ARTIFACT:
            if ie.item.name not in self._player.artifacts:
                self._player.artifacts.append(ie.item.name)
            if ie in self._level.items:
                self._level.items.remove(ie)
            got = len(self._player.artifacts)
            self._log.add(f"You claim the {ie.item.name}!  ({got}/3 relics)", Color.YELLOW)
            self._renderer.add_damage_text(self._player.x, self._player.y, "RELIC!", (255, 215, 0))
            self._renderer.add_particles(self._player.x, self._player.y, (255, 215, 0), count=20)
            self._renderer.trigger_flash(150, (255, 230, 120))
            self._sound.play("bless")
            if got >= 3:
                self._trigger_victory()
            return True
        if not self._player.inventory.add(ie.item):
            self._log.add("Your pack is full.", Color.RED)
            return False
        self._level.items.remove(ie)
        self._log.add(f"You pick up the {ie.item.display_name}.", Color.CYAN)
        self._sound.play("pickup")
        
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
            self._sound.play("potion")
            self._player.inventory.remove(item)
            self._player.update_appearance()
        elif item.kind == ItemKind.WEAPON:
            # Selecting the currently equipped weapon again unequips it.
            if self._player.inventory.equipped_weapon is item:
                self._player.inventory.equipped_weapon = None
                self._player.update_appearance()
                self._log.add(f"You unequip the {item.display_name}.", Color.GRAY)
                self._renderer.add_damage_text(self._player.x, self._player.y, "UNEQUIP", (150, 150, 155))
                return
            wand = self._player.inventory.equipped_wand
            if wand is not None:
                self._player.inventory.equipped_wand = None
                self._log.add(f"You stow the {wand.display_name}.", Color.GRAY)
            self._player.inventory.equipped_weapon = item
            self._player.update_appearance()
            self._log.add(f"You equip the {item.display_name}.", Color.CYAN)
            self._renderer.add_damage_text(self._player.x, self._player.y, "EQUIP", (45, 175, 205))
        elif item.kind == ItemKind.WAND:
            # Selecting the currently readied wand again stows it.
            if self._player.inventory.equipped_wand is item:
                self._player.inventory.equipped_wand = None
                self._log.add(f"You stow the {item.display_name}.", Color.GRAY)
                self._renderer.add_damage_text(self._player.x, self._player.y, "STOW", (150, 150, 155))
                return
            weapon = self._player.inventory.equipped_weapon
            if weapon is not None:
                self._player.inventory.equipped_weapon = None
                self._log.add(f"You stow the {weapon.display_name}.", Color.GRAY)
                self._player.update_appearance()
            self._player.inventory.equipped_wand = item
            self._log.add(f"You ready the {item.display_name}.", Color.MAGENTA)
            self._renderer.add_damage_text(self._player.x, self._player.y, "READY", (200, 60, 200))
        elif item.kind == ItemKind.KEY:
            self._log.add("Use keys by walking into locked chests.", Color.YELLOW)
        elif item.kind == ItemKind.ARROW:
            self._log.add("Arrows are used automatically when attacking with a Bow.", Color.YELLOW)
        elif item.kind == ItemKind.TOOL:
            self._log.add("Press [H], then a direction, to swing across a chasm.", Color.CYAN)

    def _drop_item(self, item: Item):
        from Items.item import ItemEntity
        inv = self._player.inventory
        if item not in inv.items:
            return

        # Find a free, walkable tile for the dropped item: the player's own
        # tile first, then the surrounding ring.
        px, py = self._player.x, self._player.y
        candidates = [(px, py)]
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0),
                       (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            candidates.append((px + dx, py + dy))

        drop_tile = None
        for cx, cy in candidates:
            if self._level.is_walkable(cx, cy) and self._level.item_at(cx, cy) is None:
                drop_tile = (cx, cy)
                break

        if drop_tile is None:
            self._log.add("No room to drop that here.", Color.RED)
            return

        inv.remove(item)  # also unequips if it was equipped
        self._player.update_appearance()
        self._level.items.append(ItemEntity(drop_tile[0], drop_tile[1], item))
        self._log.add(f"You drop the {item.display_name}.", Color.GRAY)
        self._renderer.add_damage_text(self._player.x, self._player.y, "DROP", (150, 150, 155))
        self._sound.play("walk")

    def _interact_with_npc(self, npc):
        self._sound.play("walk")
        self._renderer.add_bump(self._player, (npc.x, npc.y))
        dialogue = self._rng.choice(npc.dialogues)
        self._log.add(f"{npc.name}: \"{dialogue}\"", Color.WHITE)

    def _interact_with_chest(self, m):
        if m.is_mimic:
            # Wake up mimic!
            m.is_chest = False
            m.name = "mimic"
            self._log.add("Surprise! The chest is a Mimic!", Color.RED)
            self._renderer.add_damage_text(m.x, m.y, "MIMIC!", (240, 50, 50))
            self._renderer.add_particles(m.x, m.y, (220, 50, 50), count=18)
            self._renderer.trigger_shake(8.0)
            self._sound.play("mimic")
            
            # Immediate ambush attack
            dmg = max(1, m.attack + self._rng.randint(-1, 1))
            if getattr(self._player, "char_class", "") == "Knight":
                dmg = max(1, dmg - 1)
                self._log.add(f"The mimic bites you for {dmg} (blocked 1)!", Color.RED)
            else:
                self._log.add(f"The mimic bites you for {dmg}!", Color.RED)
                
            self._player.hp -= dmg
            self._renderer.add_damage_text(self._player.x, self._player.y, f"-{dmg}", (220, 55, 55))
            self._renderer.add_particles(self._player.x, self._player.y, (210, 50, 50), count=8)
            if not self._player.is_alive:
                self._log.add("The mimic kills you...", Color.RED)
                self._trigger_game_over()
            return

        if m.is_locked:
            key_item = None
            for item in self._player.inventory.items:
                if item.kind == ItemKind.KEY:
                    key_item = item
                    break
            
            if key_item is None:
                self._log.add("This chest is locked. You need a key to open it!", Color.YELLOW)
                self._renderer.add_damage_text(m.x, m.y, "LOCKED", (240, 200, 30))
                return
            
            # Consume key
            self._player.inventory.remove(key_item)
            self._log.add("You unlock and open the chest.", Color.GREEN)
            self._sound.play("chest")
            self._open_chest_loot(m, is_premium=True)
        else:
            self._log.add("You open the chest.", Color.GREEN)
            self._sound.play("chest")
            self._open_chest_loot(m, is_premium=False)

    def _open_chest_loot(self, m, is_premium: bool):
        if m in self._level.monsters:
            self._level.monsters.remove(m)
            
        self._renderer.add_particles(m.x, m.y, (255, 215, 0) if is_premium else (220, 180, 140), count=20)
        self._renderer.add_damage_text(m.x, m.y, "OPEN!", (255, 215, 0) if is_premium else (220, 220, 220))
        self._renderer.trigger_shake(4.0)

        from Items.item import ItemEntity, create_coin
        
        if is_premium:
            p_item = Item()
            if self._rng.random() < 0.40:
                p_item.name = "wand of lightning"
                p_item.glyph = "🪄"
                p_item.color = Color.CYAN
                p_item.kind = ItemKind.WAND
                p_item.wand_damage = 10 + self._player.depth // 2
                p_item.wand_range = 6
                p_item.charges = 4 + self._rng.randrange(3)
                p_item.max_charges = p_item.charges
            else:
                weapon_names = ["dagger", "shortsword", "longsword", "battle axe", "warhammer"]
                bonus = 2 + self._player.depth // 2 + self._rng.randrange(2)
                idx = max(0, min(bonus - 1, len(weapon_names) - 1))
                p_item.name = weapon_names[idx]
                p_item.glyph = "🗡️"
                p_item.color = Color.CYAN
                p_item.kind = ItemKind.WEAPON
                p_item.attack_bonus = bonus
                
            self._level.items.append(ItemEntity(m.x, m.y, p_item))
            self._log.add(f"A shiny {p_item.display_name} rolls out!", Color.CYAN)
            
            # Potion
            pot = Item()
            pot.name = "healing potion"
            pot.glyph = "🧪"
            pot.color = Color.RED
            pot.kind = ItemKind.HEALING_POTION
            pot.heal_amount = 12 + self._rng.randrange(8)
            nx, ny = self._find_vacant_neighbor(m.x, m.y)
            self._level.items.append(ItemEntity(nx, ny, pot))
            
            # Gold coins
            val = self._rng.randint(15, 30) + self._player.depth * 5
            nx2, ny2 = self._find_vacant_neighbor(m.x, m.y, exclude=(nx, ny))
            self._level.items.append(create_coin(nx2, ny2, val))
        else:
            roll = self._rng.random()
            if roll < 0.45:
                pot = Item()
                pot.name = "healing potion"
                pot.glyph = "🧪"
                pot.color = Color.RED
                pot.kind = ItemKind.HEALING_POTION
                pot.heal_amount = 8 + self._rng.randrange(6)
                self._level.items.append(ItemEntity(m.x, m.y, pot))
                self._log.add("A healing potion is inside!", Color.CYAN)
            elif roll < 0.70:
                p_item = Item()
                if self._rng.random() < 0.30:
                    p_item.name = "wand of lightning"
                    p_item.glyph = "🪄"
                    p_item.color = Color.CYAN
                    p_item.kind = ItemKind.WAND
                    p_item.wand_damage = 8 + self._player.depth // 3
                    p_item.wand_range = 6
                    p_item.charges = 3 + self._rng.randrange(2)
                    p_item.max_charges = 3
                else:
                    weapon_names = ["dagger", "shortsword", "longsword"]
                    bonus = 1 + self._player.depth // 2
                    idx = max(0, min(bonus - 1, len(weapon_names) - 1))
                    p_item.name = weapon_names[idx]
                    p_item.glyph = "🗡️"
                    p_item.color = Color.CYAN
                    p_item.kind = ItemKind.WEAPON
                    p_item.attack_bonus = bonus
                self._level.items.append(ItemEntity(m.x, m.y, p_item))
                self._log.add(f"A {p_item.display_name} is inside!", Color.CYAN)
            else:
                val = self._rng.randint(6, 15) + self._player.depth * 2
                self._level.items.append(create_coin(m.x, m.y, val))
                self._log.add(f"You find {val} gold coins inside!", Color.YELLOW)

    def _find_vacant_neighbor(self, x: int, y: int, exclude: tuple[int, int] = None) -> tuple[int, int]:
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,-1), (-1,1), (1,1)]:
            nx, ny = x + dx, y + dy
            if self._level.in_bounds(nx, ny):
                if self._level.tiles[nx][ny].is_walkable:
                    if exclude is None or (nx != exclude[0] or ny != exclude[1]):
                        return nx, ny
        return x, y

    def _try_descend(self) -> bool:
        if self._in_overworld:
            px, py = self._player.x, self._player.y
            ow = self._overworld
            if (px, py) == ow.stairs_down_crypt:
                dungeon_id = "crypt"
            elif (px, py) == ow.stairs_down_cellar:
                dungeon_id = "cellar"
            elif (px, py) == ow.stairs_down_cave:
                dungeon_id = "cave"
            else:
                self._log.add("No stairs down here.", Color.DARK_GRAY)
                return False
            self._enter_level(dungeon_id, 1, from_above=True)
            self._log.add(f"You enter the {dungeon_id.capitalize()} Dungeon.", Color.YELLOW)
        else:
            if self._level.tiles[self._player.x][self._player.y].type != TileType.STAIRS_DOWN:
                self._log.add("No stairs down here.", Color.DARK_GRAY)
                return False
            self._enter_level(self._current_dungeon_id, self._player.depth + 1, from_above=True)
            self._log.add(f"You descend to depth {self._player.depth}.", Color.YELLOW)
            
        self._sound.play("stairs")
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

        # Check if Bow is equipped and has arrows. If so, shoot!
        weapon = self._player.inventory.equipped_weapon
        if weapon is not None and weapon.name == "bow":
            if getattr(self._player, "flame_arrows", 0) <= 0 and getattr(self._player, "arrows", 0) <= 0:
                self._log.add("You have no arrows left!", Color.DARK_GRAY)
                return False
            self._fire_arrow(dx, dy)
            return True

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
            if getattr(monster, "is_merchant", False):
                self._active_merchant = monster
                self._state = GameState.SHOP
            elif getattr(monster, "is_chest", False):
                self._interact_with_chest(monster)
            elif getattr(monster, "is_npc", False):
                self._interact_with_npc(monster)
            else:
                self._attack_monster(monster)
            return True

        # Swing in air (visually bump and show message)
        self._renderer.add_bump(self._player, (nx, ny))
        is_enchanted = weapon is not None and getattr(weapon, "is_enchanted", False)
        slash_color = (255, 215, 0) if is_enchanted else (150, 220, 255)
        self._renderer.add_slash(nx, ny, facing, slash_color)
        self._log.add("You swing at thin air.", Color.DARK_GRAY)
        return True

    def _fire_arrow(self, dx: int, dy: int):
        is_flame = False
        if getattr(self._player, "flame_arrows", 0) > 0:
            is_flame = True
            self._player.flame_arrows -= 1
        else:
            self._player.arrows = getattr(self._player, "arrows", 0) - 1

        self._state = GameState.ANIMATING
        self._sound.play("shoot")

        x, y = self._player.x, self._player.y
        path = []
        target_monster = None
        target_wall = False

        for _ in range(10): # Range of 10 cells
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
            if self._player.is_alive:
                self._state = GameState.PLAYING
            else:
                self._trigger_game_over()
            return

        def on_projectile_complete():
            nonlocal target_monster, target_wall
            if target_wall:
                self._log.add("The arrow clatters against the wall.", Color.GRAY)
                # Drop an arrow on the floor at the last walkable tile
                if len(path) > 1:
                    drop_x, drop_y = path[-2]
                else:
                    drop_x, drop_y = self._player.x, self._player.y
                
                # Check if there is already an item there
                existing = self._level.item_at(drop_x, drop_y)
                if existing is not None and existing.item.kind == ItemKind.ARROW and existing.item.name == ("arrows of flames" if is_flame else "arrows"):
                    existing.item.charges += 1
                elif existing is None:
                    # Spawn new arrow pile containing 1 arrow
                    from Items.item import ItemEntity
                    arrow_item = Item()
                    arrow_item.name = "arrows of flames" if is_flame else "arrows"
                    arrow_item.glyph = "🏹"
                    arrow_item.color = Color.RED if is_flame else Color.GRAY
                    arrow_item.kind = ItemKind.ARROW
                    arrow_item.charges = 1
                    self._level.items.append(ItemEntity(drop_x, drop_y, arrow_item))
                    
            elif target_monster is not None:
                m = target_monster
                if getattr(m, "is_npc", False):
                    self._log.add(f"Your arrow passes harmlessly over {m.name}.", Color.DARK_GRAY)
                else:
                    # Deal damage
                    is_crit = False
                    if getattr(self._player, "char_class", "") == "Rogue" and self._rng.random() < 0.30:
                        is_crit = True
                        
                    dmg = max(1, self._player.attack + self._rng.randint(-1, 1))
                    if is_crit:
                        dmg *= 2
                        
                    m.hp -= dmg
                    self._sound.play("hit")
                    
                    if is_crit:
                        self._log.add(f"Critical strike! You shoot the {m.name} for {dmg}!", Color.YELLOW)
                        self._renderer.add_damage_text(m.x, m.y, f"CRIT! -{dmg}", (255, 215, 0))
                        self._renderer.add_particles(m.x, m.y, (255, 215, 0), count=15)
                    else:
                        self._log.add(f"You shoot the {m.name} for {dmg}.", Color.WHITE)
                        self._renderer.add_damage_text(m.x, m.y, f"-{dmg}", (220, 55, 55))
                        self._renderer.add_particles(m.x, m.y, (180, 50, 50), count=8)

                    # Flame arrow burning status application!
                    if is_flame:
                        m.burning_timer = 300 # 5 seconds
                        self._log.add(f"Your flame arrow sets the {m.name} on fire!", Color.RED)
                        self._renderer.add_particles(m.x, m.y, (255, 120, 20), count=6)

                if not m.is_alive:
                    self._log.add(f"You kill the {m.name}!", Color.GREEN)
                    self._player.kills += 1
                    if m in self._level.monsters:
                        self._level.monsters.remove(m)
                    self._drop_monster_loot(m)

            if self._player.is_alive:
                self._state = GameState.PLAYING
            else:
                self._trigger_game_over()

        # Launch arrow projectile animation on the renderer (type="flame_arrow" or "arrow")
        self._renderer.add_projectile(path, on_projectile_complete, type="flame_arrow" if is_flame else "arrow")

    GRAPPLE_RANGE = 6

    def _start_grapple(self, dx: int, dy: int):
        # Scan the chosen direction: fly over chasm tiles and land on the first
        # solid ground beyond them. A wall stops the hook; ground with no chasm
        # in between means there's nothing to swing across.
        self._state = GameState.PLAYING
        if dx == 0 and dy == 0:
            return

        if dx > 0:
            self._player.facing = "RIGHT"
        elif dx < 0:
            self._player.facing = "LEFT"
        elif dy > 0:
            self._player.facing = "DOWN"
        else:
            self._player.facing = "UP"

        px, py = self._player.x, self._player.y
        saw_chasm = False
        landing = None
        for i in range(1, self.GRAPPLE_RANGE + 1):
            tx, ty = px + dx * i, py + dy * i
            if not self._level.in_bounds(tx, ty):
                break
            ttype = self._level.tiles[tx][ty].type
            if ttype == TileType.CHASM:
                saw_chasm = True
                continue
            if ttype == TileType.WALL:
                break  # the hook can't bite into a wall
            # Solid, walkable ground.
            if saw_chasm and self._level.monster_at(tx, ty) is None:
                landing = (tx, ty)
            break

        if landing is None:
            self._log.add("No chasm to swing across that way.", Color.DARK_GRAY)
            return

        path = self._get_line_path(px, py, landing[0], landing[1])
        if not path:
            return

        self._state = GameState.ANIMATING
        self._sound.play("shoot")

        def on_complete():
            self._player.x, self._player.y = landing
            self._player.update_appearance()
            self._renderer.add_damage_text(landing[0], landing[1], "SWING!", (120, 200, 255))
            self._try_use_fountain(landing[0], landing[1])
            if self._player.is_alive:
                self._state = GameState.PLAYING
            else:
                self._trigger_game_over()

        self._renderer.add_projectile(path, on_complete, type="hook")
        self._log.add("You swing across the chasm!", Color.CYAN)

    def _start_lightning(self, dx: int, dy: int):
        wand = self._player.inventory.equipped_wand
        if wand is not None and wand.name == "wand of flames":
            self._start_fire_wand(dx, dy)
            return

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
        self._renderer.trigger_flash(alpha=160, color=(160, 220, 255))
        self._state = GameState.ANIMATING
        self._sound.play("zap")

        # Projectile callback runs when the lightning visual hits target
        def on_projectile_complete():
            nonlocal target_monster, target_wall
            if target_wall:
                self._log.add("The lightning crackles against the wall.", Color.RED)
            elif target_monster is not None:
                m = target_monster
                if getattr(m, "is_chest", False):
                    if getattr(m, "is_mimic", False):
                        m.is_chest = False
                        m.name = "mimic"
                        m.hp = 15 + m.depth * 5
                        m.max_hp = m.hp
                        m.attack = 3 + m.depth
                        
                        dmg = wand.wand_damage + self._rng.randint(-1, 1)
                        m.hp -= dmg
                        self._log.add(f"The chest reveals itself as a Mimic and takes {dmg} lightning damage!", Color.CYAN)
                        self._renderer.add_damage_text(m.x, m.y, f"-{dmg}", (50, 190, 220))
                        self._renderer.add_particles(m.x, m.y, (100, 200, 255), count=12)
                        if not m.is_alive:
                            self._log.add("The Mimic is shocked to dust!", Color.GREEN)
                            self._player.kills += 1
                            if m in self._level.monsters:
                                self._level.monsters.remove(m)
                            self._drop_monster_loot(m)
                    else:
                        self._log.add("The lightning shocks the chest harmlessly.", Color.DARK_GRAY)
                        self._renderer.add_particles(m.x, m.y, (100, 200, 255), count=4)
                else:
                    if getattr(m, "is_npc", False):
                        self._log.add(f"The lightning shocks {m.name} harmlessly.", Color.DARK_GRAY)
                    else:
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
                        self._drop_monster_loot(m)
            else:
                self._log.add("The lightning dissipates into the dark.", Color.DARK_GRAY)

            # Move state back to playing after electric hit animation
            if self._player.is_alive:
                self._state = GameState.PLAYING
            else:
                self._trigger_game_over()

        # Launch the lightning projectile animation on the renderer (type="lightning")
        self._renderer.add_projectile(path, on_projectile_complete, type="lightning")

    def _start_fire_wand(self, dx: int, dy: int):
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
            self._log.add("The fire fizzles instantly.", Color.DARK_GRAY)
            self._state = GameState.PLAYING
            return

        wand.charges -= 1
        self._renderer.trigger_flash(alpha=160, color=(255, 120, 40))
        self._state = GameState.ANIMATING
        self._sound.play("zap")

        def on_projectile_complete():
            nonlocal target_monster, target_wall
            # Set ground on fire along the path
            for (px, py) in path:
                if self._level.in_bounds(px, py) and self._level.tiles[px][py].is_walkable:
                    self._level.burning_tiles[(px, py)] = 600 # 10 seconds

            if target_wall:
                self._log.add("The fire crackles against the wall.", Color.RED)
            elif target_monster is not None:
                m = target_monster
                if getattr(m, "is_chest", False):
                    if getattr(m, "is_mimic", False):
                        m.is_chest = False
                        m.name = "mimic"
                        m.hp = 15 + m.depth * 5
                        m.max_hp = m.hp
                        m.attack = 3 + m.depth
                        
                        dmg = wand.wand_damage + self._rng.randint(-1, 1)
                        m.hp -= dmg
                        m.burning_timer = 300
                        self._log.add(f"The chest reveals itself as a Mimic and takes {dmg} fire damage!", Color.RED)
                        self._renderer.add_damage_text(m.x, m.y, f"-{dmg}", (255, 100, 0))
                        self._renderer.add_particles(m.x, m.y, (255, 120, 20), count=15)
                        if not m.is_alive:
                            self._log.add("The Mimic is burned to ashes!", Color.GREEN)
                            self._player.kills += 1
                            if m in self._level.monsters:
                                self._level.monsters.remove(m)
                            self._drop_monster_loot(m)
                    else:
                        self._log.add("The fire engulfs the chest harmlessly.", Color.DARK_GRAY)
                        self._renderer.add_particles(m.x, m.y, (255, 120, 20), count=4)
                else:
                    if getattr(m, "is_npc", False):
                        self._log.add(f"The fire washes over {m.name} harmlessly.", Color.DARK_GRAY)
                    else:
                        dmg = wand.wand_damage + self._rng.randint(-1, 1)
                        m.hp -= dmg
                        m.burning_timer = 300
                        self._log.add(f"You burn the {m.name} for {dmg}!", Color.RED)
                        self._renderer.add_damage_text(m.x, m.y, f"-{dmg}", (255, 100, 0))
                        self._renderer.add_particles(m.x, m.y, (255, 120, 20), count=12)

                        if not m.is_alive:
                            self._log.add(f"You burn the {m.name} to ashes!", Color.GREEN)
                            self._player.kills += 1
                            if m in self._level.monsters:
                                self._level.monsters.remove(m)
                            self._drop_monster_loot(m)
            else:
                self._log.add("The fire dissipates into the dark.", Color.DARK_GRAY)

            if self._player.is_alive:
                self._state = GameState.PLAYING
            else:
                self._trigger_game_over()

        self._renderer.add_projectile(path, on_projectile_complete, type="fireball")

    def _try_ascend(self) -> bool:
        if self._in_overworld:
            self._log.add("You cannot ascend from the overworld.", Color.DARK_GRAY)
            return False
        if self._level.tiles[self._player.x][self._player.y].type != TileType.STAIRS_UP:
            self._log.add("No stairs up here.", Color.DARK_GRAY)
            return False
        if self._player.depth <= 1:
            self._enter_level("", 0, from_above=False)
            self._log.add("You ascend to the Overworld.", Color.YELLOW)
        else:
            self._enter_level(self._current_dungeon_id, self._player.depth - 1, from_above=False)
            self._log.add(f"You ascend to depth {self._player.depth}.", Color.YELLOW)
            
        self._sound.play("stairs")
        self._renderer.trigger_shake(8.0)
        self._renderer.add_particles(self._player.x, self._player.y, (245, 245, 245), count=15)
        return True

    def _get_line_path(self, x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
        path = []
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return []
        for i in range(1, steps + 1):
            x = x1 + round(dx * i / steps)
            y = y1 + round(dy * i / steps)
            path.append((x, y))
        return path

    def _try_monster_ranged(self, m: Monster, dx: int, dy: int) -> bool:
        """Fire a monster's ranged attack at the player if in range, off
        cooldown, and with a clear line of fire. Returns True if it fired."""
        if getattr(m, "ranged_cooldown", 0) > 0:
            m.ranged_cooldown -= 1

        dist = abs(dx) + abs(dy)
        if not (1 < dist <= getattr(m, "ranged_range", 5)):
            return False
        if getattr(m, "ranged_cooldown", 0) > 0:
            return False

        # Require an unobstructed straight path to the player.
        path = self._get_line_path(m.x, m.y, self._player.x, self._player.y)
        if not path:
            return False
        for px, py in path[:-1]:
            if not self._level.tiles[px][py].is_walkable:
                return False

        m.ranged_cooldown = getattr(m, "ranged_cooldown_max", 3)
        self._state = GameState.ANIMATING
        self._sound.play("shoot")
        rtype = m.ranged  # "arrow" or "fireball"
        dest = path[-1]

        def on_complete():
            # Only connects if the player is still on the targeted tile.
            if self._player.x == dest[0] and self._player.y == dest[1]:
                dmg = max(1, m.attack + self._rng.randint(-1, 1))
                if getattr(self._player, "char_class", "") == "Knight":
                    dmg = max(1, dmg - 1)
                self._player.hp -= dmg
                self._renderer.add_damage_text(self._player.x, self._player.y, f"-{dmg}", (220, 55, 55))
                self._renderer.trigger_shake(6.0)
                if rtype == "fireball":
                    self._log.add(f"The {m.name}'s fireball scorches you for {dmg}!", Color.RED)
                    self._renderer.add_particles(self._player.x, self._player.y, (255, 100, 0), count=12)
                    if getattr(self._player, "burning_timer", 0) < 120:
                        self._player.burning_timer = 120
                else:
                    self._log.add(f"The {m.name}'s arrow strikes you for {dmg}!", Color.RED)
                    self._renderer.add_particles(self._player.x, self._player.y, (210, 50, 50), count=8)
            else:
                self._log.add(f"The {m.name}'s {rtype} whistles past you.", Color.DARK_GRAY)

            if self._player.is_alive:
                self._state = GameState.PLAYING
            else:
                self._trigger_game_over()

        self._renderer.add_projectile(path, on_complete, type=rtype)
        return True

    def _monsters_act(self):
        for m in list(self._level.monsters):
            if not m.is_alive:
                continue
            if getattr(m, "is_merchant", False):
                continue
            if getattr(m, "is_chest", False):
                continue
            if getattr(m, "is_npc", False):
                continue
            if not self._level.tiles[m.x][m.y].visible:
                continue

            dx = self._player.x - m.x
            dy = self._player.y - m.y

            if abs(dx) + abs(dy) == 1:
                dmg = max(1, m.attack + self._rng.randint(-1, 1))
                if getattr(self._player, "char_class", "") == "Knight":
                    dmg = max(1, dmg - 1)
                self._player.hp -= dmg
                self._sound.play("hit")
                
                if getattr(self._player, "char_class", "") == "Knight":
                    self._log.add(f"The {m.name} hits you for {dmg} (blocked 1).", Color.RED)
                else:
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

            # Ranged attackers (trolls shoot arrows, witches hurl fireballs)
            if getattr(m, "ranged", None):
                if self._try_monster_ranged(m, dx, dy):
                    continue

            # Dragon Fire Breath AI
            if m.name == "dragon":
                if getattr(m, "fire_cooldown", 0) > 0:
                    m.fire_cooldown -= 1
                
                dist = abs(dx) + abs(dy)
                if 1 < dist <= 6:
                    if getattr(m, "fire_cooldown", 0) <= 0:
                        path = self._get_line_path(m.x, m.y, self._player.x, self._player.y)
                        blocked = False
                        for px, py in path[:-1]:
                            if not self._level.tiles[px][py].is_walkable:
                                blocked = True
                                break
                        if not blocked:
                            m.fire_cooldown = 4
                            self._state = GameState.ANIMATING
                            self._sound.play("shoot")
                            
                            def on_dragon_fire_complete():
                                if self._player.x == path[-1][0] and self._player.y == path[-1][1]:
                                    dmg = max(1, m.attack + self._rng.randint(-1, 1))
                                    self._player.hp -= dmg
                                    if getattr(self._player, "burning_timer", 0) < 180:
                                        self._player.burning_timer = 180
                                    self._log.add(f"The dragon breathes fire on you for {dmg} damage!", Color.RED)
                                    self._renderer.add_damage_text(self._player.x, self._player.y, f"-{dmg}", (255, 50, 50))
                                    self._renderer.add_particles(self._player.x, self._player.y, (255, 100, 0), count=12)
                                    self._renderer.trigger_shake(6.0)
                                
                                for px, py in path:
                                    if self._level.in_bounds(px, py) and self._level.tiles[px][py].is_walkable:
                                        self._level.burning_tiles[(px, py)] = 600
                                        
                                if self._player.is_alive:
                                    self._state = GameState.PLAYING
                                else:
                                    self._trigger_game_over()
                                    
                            self._renderer.add_projectile(path, on_dragon_fire_complete, type="fireball")
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

    def _buy_shop_item(self, slot_idx: int):
        merchant = self._active_merchant
        if not merchant or slot_idx < 0 or slot_idx >= len(merchant.shop_items):
            return

        item, price, is_sold_out = merchant.shop_items[slot_idx]
        if is_sold_out:
            self._log.add("That item is already sold out!", Color.DARK_GRAY)
            return

        if self._player.coins < price:
            self._log.add("Not enough gold!", Color.RED)
            return

        # Handle the custom service (Bless Weapon)
        if item.name == "bless weapon":
            weapon = self._player.inventory.equipped_weapon
            if weapon is None:
                self._log.add("You have no weapon equipped to bless!", Color.YELLOW)
                return
            if weapon.is_enchanted:
                self._log.add(f"Your {weapon.display_name} is already enchanted!", Color.DARK_GRAY)
                return
            
            # Enchant!
            self._player.coins -= price
            weapon.is_enchanted = True
            self._player.update_appearance()
            merchant.shop_items[slot_idx][2] = True  # Mark sold out
            self._log.add(f"Your {weapon.display_name} glows with enchantment!", Color.CYAN)
            self._sound.play("bless")
            self._renderer.add_particles(self._player.x, self._player.y, (240, 200, 30), count=25)
            self._renderer.add_damage_text(self._player.x, self._player.y, "BLESSED!", (240, 200, 30))
            return

        # Handle purchasing arrows (adds to arrow pool, bypasses inventory pack full check)
        if item.kind == ItemKind.ARROW:
            self._player.coins -= price
            self._player.arrows = getattr(self._player, "arrows", 0) + item.charges
            merchant.shop_items[slot_idx][2] = True  # Mark sold out
            self._log.add(f"You bought {item.charges} arrows!", Color.GREEN)
            self._sound.play("pickup")
            self._renderer.add_damage_text(self._player.x, self._player.y, f"+{item.charges} Arrows", (200, 200, 200))
            self._renderer.add_particles(self._player.x, self._player.y, (220, 220, 220), count=10)
            return

        # Handle standard items (added to backpack)
        # Check if pack is full
        if len(self._player.inventory.items) >= 20:
            self._log.add("Your pack is full!", Color.RED)
            return

        # Deduct gold and add item
        self._player.coins -= price
        self._player.inventory.add(item)
        merchant.shop_items[slot_idx][2] = True  # Mark sold out
        self._log.add(f"You bought the {item.name}!", Color.GREEN)
        self._sound.play("pickup")
        self._renderer.add_damage_text(self._player.x, self._player.y, "BOUGHT", (50, 200, 70))
        self._renderer.add_particles(self._player.x, self._player.y, (50, 200, 70), count=10)





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
