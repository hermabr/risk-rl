from risk.game import Game
from risk.player_io import PlayerIO

game = Game([PlayerIO("Player 1"), PlayerIO("Player 2"), PlayerIO("Player 3")])
game.gameplay_loop()
