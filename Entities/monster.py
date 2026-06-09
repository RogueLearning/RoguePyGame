from Entities.entity import Entity


class Monster(Entity):
    def __init__(self):
        super().__init__()
        self.hp: int = 0
        self.max_hp: int = 0
        self.attack: int = 0
        self.is_boss: bool = False

    @property
    def is_alive(self) -> bool:
        return self.hp > 0
