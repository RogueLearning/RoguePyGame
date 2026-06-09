import random
from enum import Enum

from UI.colors import Color


class ItemKind(Enum):
    HEALING_POTION = "healing_potion"
    WEAPON = "weapon"
    WAND = "wand"


class Item:
    def __init__(self):
        self.name: str = ""
        self.glyph: str = "??"
        self.color: Color = Color.GRAY
        self.kind: ItemKind = ItemKind.HEALING_POTION
        self.heal_amount: int = 0
        self.attack_bonus: int = 0
        self.is_enchanted: bool = False
        self.charges: int = 0
        self.wand_damage: int = 0
        self.wand_range: int = 0

    @property
    def display_name(self) -> str:
        if self.kind == ItemKind.WEAPON and self.is_enchanted:
            return f"enchanted {self.name}"
        if self.kind == ItemKind.WAND:
            return f"{self.name} ({self.charges})"
        return self.name


class ItemEntity:
    def __init__(self, x: int = 0, y: int = 0, item: Item | None = None):
        self.x = x
        self.y = y
        self.item = item if item is not None else Item()


_WEAPON_NAMES = ["dagger", "shortsword", "longsword", "battle axe", "warhammer"]


def create(x: int, y: int, depth: int, rng: random.Random) -> ItemEntity:
    ie = ItemEntity(x=x, y=y)
    if depth >= 2 and rng.randrange(100) < 15:
        item = Item()
        item.name = "wand of lightning"
        item.glyph = "🪄"
        item.color = Color.CYAN  # Cyan color fits lightning perfectly!
        item.kind = ItemKind.WAND
        item.wand_damage = 8 + depth // 3
        item.wand_range = 6
        item.charges = 3 + rng.randrange(3)
        ie.item = item
    elif rng.randrange(100) < 55:
        item = Item()
        item.name = "healing potion"
        item.glyph = "🧪"
        item.color = Color.RED
        item.kind = ItemKind.HEALING_POTION
        item.heal_amount = 10 + rng.randrange(6)
        ie.item = item
    else:
        bonus = 1 + depth // 2 + rng.randrange(2)
        idx = max(0, min(bonus - 1, len(_WEAPON_NAMES) - 1))
        item = Item()
        item.name = _WEAPON_NAMES[idx]
        item.glyph = "🗡️"
        item.color = Color.CYAN
        item.kind = ItemKind.WEAPON
        item.attack_bonus = bonus
        ie.item = item
    return ie
