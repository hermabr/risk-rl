from risk.game import Game
from risk.player_io import PlayerIO
from risk.player_heuristic import PlayerHeuristic
import risk.logging_setup as logging_setup
import logging
import traceback

logging_setup.init_logging()


players = [PlayerHeuristic("Player 1"), PlayerHeuristic("Player 2"),
            PlayerHeuristic("Player 3"), PlayerHeuristic("Player 4")]

game = Game(players, display_map=False, delay=False) 

try:
    game.gameplay_loop()
except Exception as e:
    logging.error("An error occurred: %s", str(e))
    logging.error("Stack trace: %s", traceback.format_exc())
