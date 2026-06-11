import random
from Entities.monster import Monster
from UI.colors import Color


class Chest(Monster):
    def __init__(self, is_locked: bool = False, is_mimic: bool = False, depth: int = 1, rng: random.Random = None):
        super().__init__()
        self.is_chest = True
        self.is_locked = is_locked
        self.is_mimic = is_mimic
        self.depth = depth
        
        if is_mimic:
            self.name = "chest"  # Disguised initially
            self.hp = 15 + depth * 5
            self.max_hp = self.hp
            self.attack = 3 + depth
            self.color = Color.YELLOW
            self.glyph = "📦"
        else:
            self.name = "locked chest" if is_locked else "chest"
            self.hp = 99999  # Normal chests are invulnerable
            self.max_hp = 99999
            self.attack = 0
            self.color = Color.YELLOW if is_locked else Color.WHITE
            self.glyph = "🔒" if is_locked else "📦"
