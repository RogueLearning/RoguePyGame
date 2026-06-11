import random
from Entities.monster import Monster
from UI.colors import Color


class NPC(Monster):
    def __init__(self, name: str, npc_type: str, glyph: str, color: Color, dialogues: list[str], x: int = 0, y: int = 0):
        super().__init__()
        self.is_npc = True
        self.is_chest = False
        self.is_merchant = False
        self.name = name
        self.npc_type = npc_type  # "villager", "farmer", "ghost_npc", "druid"
        self.dialogues = dialogues
        self.glyph = glyph
        self.color = color
        self.hp = 99999
        self.max_hp = 99999
        self.attack = 0
        self.x = x
        self.y = y
