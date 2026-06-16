import random

from Entities.monster import Monster
from UI.colors import Color


def create_boss(x: int, y: int) -> Monster:
    m = Monster()
    m.name = "dread knight"
    m.glyph = "💀"
    m.color = Color.DARK_RED
    m.hp = 45
    m.max_hp = 45
    m.attack = 11
    m.is_boss = True
    m.x = x
    m.y = y
    return m


# Each dungeon ends in a unique boss guarding a unique artifact. `sprite`
# reuses an existing spritesheet; `artifact` is the relic dropped on death.
_BOSS_DEFS = {
    "crypt":  dict(name="Bonelord", sprite="dread knight", hp=55, atk=12,
                   color=Color.DARK_RED, artifact="Soul Gem"),
    "cellar": dict(name="Orc Warlord", sprite="orc", hp=64, atk=13,
                   color=Color.DARK_GREEN, artifact="Iron Crown"),
    "cave":   dict(name="Ancient Wyrm", sprite="dragon", hp=74, atk=14,
                   color=Color.RED, artifact="Dragon Heart", ranged="fireball"),
}


def create_dungeon_boss(dungeon_id: str, x: int, y: int) -> Monster:
    d = _BOSS_DEFS.get(dungeon_id, _BOSS_DEFS["crypt"])
    m = Monster()
    m.name = d["name"]
    m.sprite = d["sprite"]          # renderer uses this for the spritesheet
    m.glyph = "💀"
    m.color = d["color"]
    m.hp = d["hp"]
    m.max_hp = d["hp"]
    m.attack = d["atk"]
    m.is_boss = True
    m.dungeon_id = dungeon_id
    m.artifact = d["artifact"]
    if d.get("ranged"):
        m.ranged = d["ranged"]
        m.ranged_range = 6
        m.ranged_cooldown = 0
        m.ranged_cooldown_max = 3
    m.x = x
    m.y = y
    return m


def _make(name: str, glyph: str, color: Color, hp: int, atk: int) -> Monster:
    m = Monster()
    m.name = name
    m.glyph = glyph
    m.color = color
    m.hp = hp
    m.max_hp = hp
    m.attack = atk
    return m


def _make_ranged(name: str, glyph: str, color: Color, hp: int, atk: int,
                 ranged: str, ranged_range: int, cooldown: int) -> Monster:
    """A monster that can attack from a distance ('arrow' or 'fireball')."""
    m = _make(name, glyph, color, hp, atk)
    m.ranged = ranged              # projectile type to throw/shoot
    m.ranged_range = ranged_range  # max tiles it will fire from
    m.ranged_cooldown = 0          # turns until it can fire again
    m.ranged_cooldown_max = cooldown
    return m


def _make_dragon() -> Monster:
    m = Monster()
    m.name = "dragon"
    m.glyph = "🐉"
    m.color = Color.RED
    m.hp = 35
    m.max_hp = 35
    m.attack = 8
    m.fire_cooldown = 0
    return m


def create(x: int, y: int, depth: int, rng: random.Random) -> Monster:
    pool = [(6, lambda: _make("rat", "🐀", Color.DARK_GRAY, 4, 2))]
    if depth >= 2:
        pool.append((5, lambda: _make("goblin", "👺", Color.GREEN, 8, 3)))
    if depth >= 3:
        pool.append((4, lambda: _make("orc", "👹", Color.DARK_GREEN, 14, 5)))
    if depth >= 4:
        pool.append((2, _make_dragon))
        # Witches hurl fireballs from afar.
        pool.append((3, lambda: _make_ranged("witch", "🧙", Color.MAGENTA, 18, 6,
                                             "fireball", 6, 4)))
    if depth >= 5:
        # Trolls now loose arrows at range, then close in to club you.
        pool.append((3, lambda: _make_ranged("troll", "🧌", Color.MAGENTA, 24, 7,
                                             "arrow", 5, 3)))
    if depth >= 5:
        pool.append((2, lambda: _make("wraith", "👻", Color.CYAN, 32, 10)))

    total = sum(w for w, _ in pool)
    roll = rng.randrange(total)
    acc = 0
    chosen = pool[0][1]
    for w, make in pool:
        acc += w
        if roll < acc:
            chosen = make
            break
    m = chosen()
    m.x = x
    m.y = y
    return m
