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


def _make(name: str, glyph: str, color: Color, hp: int, atk: int) -> Monster:
    m = Monster()
    m.name = name
    m.glyph = glyph
    m.color = color
    m.hp = hp
    m.max_hp = hp
    m.attack = atk
    return m


def create(x: int, y: int, depth: int, rng: random.Random) -> Monster:
    pool = [(6, lambda: _make("rat", "🐀", Color.DARK_GRAY, 4, 2))]
    if depth >= 2:
        pool.append((5, lambda: _make("goblin", "👺", Color.GREEN, 8, 3)))
    if depth >= 3:
        pool.append((4, lambda: _make("orc", "👹", Color.DARK_GREEN, 14, 5)))
    if depth >= 5:
        pool.append((3, lambda: _make("troll", "🧌", Color.MAGENTA, 24, 7)))
    if depth >= 7:
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
