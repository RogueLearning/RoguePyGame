import random
from Entities.monster import Monster
from UI.colors import Color
from Items.item import Item, ItemKind


class Merchant(Monster):
    def __init__(self, depth: int, rng: random.Random):
        super().__init__()
        self.name = "merchant"
        self.glyph = "🏪"
        self.color = Color.YELLOW
        self.hp = 9999
        self.max_hp = 9999
        self.attack = 0
        self.is_boss = False
        self.is_merchant = True
        
        # Generate shop items: a list of [Item, gold_price, is_sold_out]
        # We use a list of lists instead of tuples so we can easily mutate the is_sold_out status!
        self.shop_items = self._generate_shop_items(depth, rng)

    def _generate_shop_items(self, depth: int, rng: random.Random) -> list[list]:
        items = []

        # Slot 1: Healing Potion (15 gold)
        potion = Item()
        potion.name = "healing potion"
        potion.glyph = "🧪"
        potion.color = Color.RED
        potion.kind = ItemKind.HEALING_POTION
        potion.heal_amount = 10 + rng.randrange(6)
        items.append([potion, 15, False])

        # Slot 2: Scaling Weapon
        weapon_names = ["dagger", "shortsword", "longsword", "battle axe", "warhammer"]
        bonus = 1 + depth // 2 + rng.randrange(2)
        weapon = Item()
        if rng.randrange(100) < 25:
            weapon.name = "bow"
            weapon.glyph = "🏹"
            weapon.color = Color.CYAN
            weapon.kind = ItemKind.WEAPON
            weapon.attack_bonus = bonus
        else:
            idx = max(0, min(bonus - 1, len(weapon_names) - 1))
            weapon.name = weapon_names[idx]
            weapon.glyph = "🗡️"
            weapon.color = Color.CYAN
            weapon.kind = ItemKind.WEAPON
            weapon.attack_bonus = bonus
        price = 20 + bonus * 10
        items.append([weapon, price, False])

        # Slot 3: Wand of Lightning (55 gold)
        wand = Item()
        wand.name = "wand of lightning"
        wand.glyph = "🪄"
        wand.color = Color.CYAN
        wand.kind = ItemKind.WAND
        wand.wand_damage = 8 + depth // 3
        wand.wand_range = 6
        wand.charges = 3 + rng.randrange(3)
        items.append([wand, 55, False])

        # Slot 4: Grappling Hook (40g) / Quiver of Arrows (15g) / Enchant (50g)
        slot4_roll = rng.randrange(100)
        if slot4_roll < 30:
            from Items.item import make_grapple
            items.append([make_grapple(), 40, False])
        elif slot4_roll < 55:
            arrows = Item()
            arrows.name = "quiver of arrows"
            arrows.glyph = "🏹"
            arrows.color = Color.GRAY
            arrows.kind = ItemKind.ARROW
            arrows.charges = 15
            items.append([arrows, 15, False])
        else:
            enchant = Item()
            enchant.name = "bless weapon"
            enchant.glyph = "✨"
            enchant.color = Color.YELLOW
            enchant.kind = ItemKind.HEALING_POTION  # dummy kind, checked by name
            items.append([enchant, 50, False])

        return items
