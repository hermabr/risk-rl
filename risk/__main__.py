from risk.game import Game
from risk.player_io import PlayerIO
from risk.player_heuristic import PlayerHeuristic

game = Game([PlayerIO("Player 1"), PlayerHeuristic("Player 2"), PlayerHeuristic("Player 3")])
game.gameplay_loop()
