from risk.player import Player

class Army:
    def __init__(self, owner: Player, n_soldiers: int):
        self.owner = owner
        self.n_soldiers = n_soldiers