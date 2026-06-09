from Entities.entity import Entity
from Items.inventory import Inventory
from UI.colors import Color


_DEFAULT_COLOR = Color.WHITE
_ENCHANTED_WEAPON_COLOR = Color.YELLOW


class Player(Entity):
    def __init__(self):
        super().__init__()
        self.hp: int = 30
        self.max_hp: int = 30
        self.base_attack: int = 4
        self.depth: int = 1
        self.max_depth: int = 1
        self.kills: int = 0
        self.inventory = Inventory()
        self.glyph = "🧙"
        self.color = _DEFAULT_COLOR
        self.name = "you"

    @property
    def attack(self) -> int:
        bonus = self.inventory.equipped_weapon.attack_bonus if self.inventory.equipped_weapon else 0
        return self.base_attack + bonus

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def score(self) -> int:
        return self.max_depth * 100 + self.kills * 10

    def update_appearance(self):
        weapon = self.inventory.equipped_weapon
        self.color = _ENCHANTED_WEAPON_COLOR if (weapon and weapon.is_enchanted) else _DEFAULT_COLOR
