from Items.item import Item


class Inventory:
    def __init__(self):
        self.items: list[Item] = []
        self.equipped_weapon: Item | None = None
        self.equipped_wand: Item | None = None
        self.capacity: int = 20

    def add(self, item: Item) -> bool:
        if len(self.items) >= self.capacity:
            return False
        self.items.append(item)
        return True

    def remove(self, item: Item):
        if item in self.items:
            self.items.remove(item)
        if self.equipped_weapon is item:
            self.equipped_weapon = None
        if self.equipped_wand is item:
            self.equipped_wand = None
