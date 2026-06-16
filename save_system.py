"""
save_system.py
------------------------------------------------------------------
Save / load support with up to 3 "campaign" slots, each holding a
single active save point.  The whole world is captured: the player and
inventory, every generated level (tiles + explored fog-of-war), all
monsters / chests / NPCs / the merchant, dropped items, burning tiles,
and the recent message log.

Saves are plain JSON under ./saves/campaign_<n>.json so they're easy to
inspect and survive code changes (unknown fields are ignored, missing
ones fall back to sensible defaults).

This module imports only the data classes -- never game.py -- so there
is no import cycle (game.py imports this).
"""

import datetime
import json
import os

from UI.colors import Color
from UI.message_log import MessageLog
from Entities.monster import Monster
from Items.item import Item, ItemEntity, ItemKind
from Map.dungeon_level import DungeonLevel
from Map.tile import TileType

SAVE_VERSION = 1
SAVE_DIR = "saves"
NUM_CAMPAIGNS = 3

# Stable ordering so tile types survive as small ints.
# Append-only ordering so existing saves keep mapping correctly.
_TILE_TYPES = [TileType.WALL, TileType.FLOOR, TileType.STAIRS_DOWN,
               TileType.STAIRS_UP, TileType.FOUNTAIN, TileType.CHASM]
_TILE_INDEX = {t: i for i, t in enumerate(_TILE_TYPES)}

_ITEM_FIELDS = ["name", "glyph", "heal_amount", "attack_bonus", "is_enchanted",
                "charges", "wand_damage", "wand_range", "coin_value"]

# Optional monster attributes worth preserving (set on various subclasses).
_MONSTER_OPT = ["is_boss", "is_chest", "is_locked", "is_mimic", "is_npc",
                "is_merchant", "depth", "fire_cooldown", "ranged", "ranged_range",
                "ranged_cooldown", "ranged_cooldown_max", "npc_type"]


# ------------------------------------------------------------------
# Items
# ------------------------------------------------------------------
def serialize_item(it: Item) -> dict:
    d = {k: getattr(it, k) for k in _ITEM_FIELDS}
    d["color"] = int(it.color)
    d["kind"] = it.kind.value
    if hasattr(it, "max_charges"):
        d["max_charges"] = it.max_charges
    return d


def deserialize_item(d: dict) -> Item:
    it = Item()
    for k in _ITEM_FIELDS:
        if k in d:
            setattr(it, k, d[k])
    it.color = Color(d.get("color", int(Color.GRAY)))
    it.kind = ItemKind(d.get("kind", ItemKind.HEALING_POTION.value))
    if "max_charges" in d:
        it.max_charges = d["max_charges"]
    return it


# ------------------------------------------------------------------
# Monsters / chests / NPCs / merchant (all duck-typed Monster subclasses)
# ------------------------------------------------------------------
def serialize_monster(m: Monster) -> dict:
    d = {
        "name": m.name,
        "x": m.x,
        "y": m.y,
        "hp": m.hp,
        "max_hp": m.max_hp,
        "attack": m.attack,
        "glyph": getattr(m, "glyph", "??"),
        "color": int(getattr(m, "color", Color.GRAY)),
        "burning_timer": getattr(m, "burning_timer", 0),
    }
    for k in _MONSTER_OPT:
        if hasattr(m, k):
            d[k] = getattr(m, k)
    if hasattr(m, "dialogues"):
        d["dialogues"] = list(m.dialogues)
    if hasattr(m, "shop_items"):
        d["shop_items"] = [[serialize_item(it), price, sold]
                           for (it, price, sold) in m.shop_items]
    return d


def deserialize_monster(d: dict) -> Monster:
    m = Monster()
    m.name = d.get("name", "")
    m.x = d.get("x", 0)
    m.y = d.get("y", 0)
    m.hp = d.get("hp", 1)
    m.max_hp = d.get("max_hp", 1)
    m.attack = d.get("attack", 0)
    m.glyph = d.get("glyph", "??")
    m.color = Color(d.get("color", int(Color.GRAY)))
    m.burning_timer = d.get("burning_timer", 0)
    for k in _MONSTER_OPT:
        if k in d:
            setattr(m, k, d[k])
    if "dialogues" in d:
        m.dialogues = list(d["dialogues"])
    if "shop_items" in d:
        m.shop_items = [[deserialize_item(it), price, sold]
                        for (it, price, sold) in d["shop_items"]]
    return m


# ------------------------------------------------------------------
# Levels
# ------------------------------------------------------------------
def serialize_level(level: DungeonLevel) -> dict:
    # Each tile -> one int encoding (type_index, explored). visible is
    # recomputed by FOV every frame, so it isn't persisted.
    tiles = []
    for x in range(level.width):
        col = []
        for y in range(level.height):
            t = level.tiles[x][y]
            col.append(_TILE_INDEX.get(t.type, 0) * 2 + (1 if t.explored else 0))
        tiles.append(col)

    return {
        "width": level.width,
        "height": level.height,
        "is_overworld": level.is_overworld,
        "has_stairs_up": level.has_stairs_up,
        "stairs_down": list(level.stairs_down),
        "stairs_up": list(level.stairs_up),
        "player_spawn": list(level.player_spawn),
        "stairs_down_crypt": list(level.stairs_down_crypt),
        "stairs_down_cellar": list(level.stairs_down_cellar),
        "stairs_down_cave": list(level.stairs_down_cave),
        "burning_tiles": [[x, y, t] for (x, y), t in level.burning_tiles.items()],
        "tiles": tiles,
        "monsters": [serialize_monster(m) for m in level.monsters],
        "items": [{"x": ie.x, "y": ie.y, "item": serialize_item(ie.item)}
                  for ie in level.items],
    }


def deserialize_level(d: dict) -> DungeonLevel:
    lvl = DungeonLevel(d["width"], d["height"])
    lvl.is_overworld = d.get("is_overworld", False)
    lvl.has_stairs_up = d.get("has_stairs_up", False)
    lvl.stairs_down = tuple(d.get("stairs_down", (0, 0)))
    lvl.stairs_up = tuple(d.get("stairs_up", (0, 0)))
    lvl.player_spawn = tuple(d.get("player_spawn", (0, 0)))
    lvl.stairs_down_crypt = tuple(d.get("stairs_down_crypt", (0, 0)))
    lvl.stairs_down_cellar = tuple(d.get("stairs_down_cellar", (0, 0)))
    lvl.stairs_down_cave = tuple(d.get("stairs_down_cave", (0, 0)))
    lvl.burning_tiles = {(x, y): t for x, y, t in d.get("burning_tiles", [])}

    tiles = d["tiles"]
    for x in range(lvl.width):
        for y in range(lvl.height):
            val = tiles[x][y]
            t = lvl.tiles[x][y]
            t.type = _TILE_TYPES[val // 2]
            t.explored = bool(val % 2)
            t.visible = False

    lvl.monsters = [deserialize_monster(m) for m in d.get("monsters", [])]
    lvl.items = [ItemEntity(i["x"], i["y"], deserialize_item(i["item"]))
                 for i in d.get("items", [])]
    return lvl


# ------------------------------------------------------------------
# Player
# ------------------------------------------------------------------
def serialize_player(player) -> dict:
    inv = player.inventory
    items = inv.items

    def idx_of(it):
        return items.index(it) if it in items else -1

    return {
        "x": player.x, "y": player.y,
        "hp": player.hp, "max_hp": player.max_hp,
        "base_attack": player.base_attack,
        "depth": player.depth, "max_depth": player.max_depth,
        "kills": player.kills, "coins": player.coins,
        "arrows": getattr(player, "arrows", 0),
        "flame_arrows": getattr(player, "flame_arrows", 0),
        "char_class": getattr(player, "char_class", "Wizard"),
        "facing": getattr(player, "facing", "DOWN"),
        "burning_timer": getattr(player, "burning_timer", 0),
        "glyph": player.glyph,
        "color": int(player.color),
        "name": player.name,
        "inventory": {
            "capacity": inv.capacity,
            "items": [serialize_item(it) for it in items],
            "equipped_weapon": idx_of(inv.equipped_weapon),
            "equipped_wand": idx_of(inv.equipped_wand),
        },
    }


def apply_player(player, d: dict):
    player.x = d["x"]; player.y = d["y"]
    player.hp = d["hp"]; player.max_hp = d["max_hp"]
    player.base_attack = d.get("base_attack", 4)
    player.depth = d.get("depth", 0); player.max_depth = d.get("max_depth", 1)
    player.kills = d.get("kills", 0); player.coins = d.get("coins", 0)
    player.arrows = d.get("arrows", 0)
    player.flame_arrows = d.get("flame_arrows", 0)
    player.char_class = d.get("char_class", "Wizard")
    player.facing = d.get("facing", "DOWN")
    player.burning_timer = d.get("burning_timer", 0)
    player.glyph = d.get("glyph", player.glyph)
    player.color = Color(d.get("color", int(Color.WHITE)))
    player.name = d.get("name", "you")

    invd = d.get("inventory", {})
    inv = player.inventory
    inv.capacity = invd.get("capacity", 20)
    inv.items = [deserialize_item(x) for x in invd.get("items", [])]
    ew = invd.get("equipped_weapon", -1)
    ewd = invd.get("equipped_wand", -1)
    inv.equipped_weapon = inv.items[ew] if 0 <= ew < len(inv.items) else None
    inv.equipped_wand = inv.items[ewd] if 0 <= ewd < len(inv.items) else None


# ------------------------------------------------------------------
# Whole-game snapshot
# ------------------------------------------------------------------
def _build_meta(game) -> dict:
    p = game._player
    if game._in_overworld:
        location = "Overworld"
    else:
        place = (game._current_dungeon_id or "dungeon").capitalize()
        location = f"{place} - Depth {p.depth}"
    return {
        "char_class": getattr(p, "char_class", "Wizard"),
        "depth": p.depth,
        "max_depth": p.max_depth,
        "score": p.score,
        "kills": p.kills,
        "coins": p.coins,
        "location": location,
        "saved_at": "",  # filled in by save_campaign
    }


def serialize_game(game) -> dict:
    levels = []
    for (did, depth), lvl in game._levels.items():
        levels.append({"key": [did, depth], "level": serialize_level(lvl)})

    return {
        "version": SAVE_VERSION,
        "meta": _build_meta(game),
        "player": serialize_player(game._player),
        "world": {
            "in_overworld": game._in_overworld,
            "current_dungeon_id": game._current_dungeon_id,
            "boss_spawned": game._boss_spawned,
            "overworld": serialize_level(game._overworld),
            "levels": levels,
        },
        "log": [[t, int(c)] for (t, c) in game._log.recent],
    }


def apply_save(game, data: dict):
    apply_player(game._player, data["player"])

    w = data["world"]
    game._in_overworld = w.get("in_overworld", True)
    game._current_dungeon_id = w.get("current_dungeon_id", "")
    game._boss_spawned = w.get("boss_spawned", False)
    game._overworld = deserialize_level(w["overworld"])

    game._levels = {}
    for entry in w.get("levels", []):
        did, depth = entry["key"]
        game._levels[(did, depth)] = deserialize_level(entry["level"])

    if game._in_overworld:
        game._level = game._overworld
    else:
        game._level = game._levels.get(
            (game._current_dungeon_id, game._player.depth), game._overworld)

    game._log = MessageLog()
    for t, c in data.get("log", []):
        game._log.add(t, Color(c))


# ------------------------------------------------------------------
# File slots
# ------------------------------------------------------------------
def slot_path(slot: int) -> str:
    return os.path.join(SAVE_DIR, f"campaign_{slot}.json")


def save_campaign(game, slot: int):
    os.makedirs(SAVE_DIR, exist_ok=True)
    data = serialize_game(game)
    data["meta"]["saved_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    # Write atomically so a crash mid-write can't corrupt an existing save.
    tmp = slot_path(slot) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, slot_path(slot))


def load_campaign(game, slot: int) -> bool:
    path = slot_path(slot)
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    apply_save(game, data)
    return True


def campaign_meta(slot: int):
    """Return the lightweight meta dict for a slot, or None if empty/unreadable."""
    path = slot_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("meta")
    except Exception:
        return None


def list_campaigns():
    return [campaign_meta(s) for s in range(1, NUM_CAMPAIGNS + 1)]


def delete_campaign(slot: int):
    path = slot_path(slot)
    if os.path.exists(path):
        os.remove(path)
