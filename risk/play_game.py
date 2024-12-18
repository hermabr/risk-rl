from risk.game import Game
from risk.player_io import PlayerIO
from risk.player_heuristic import PlayerHeuristic
import risk.logging_setup as logging_setup
import logging
import traceback

def play():
    logging_setup.init_logging("Playing_IO")

    # include RL players later
    players = [PlayerIO("Player IO 1"), PlayerHeuristic("Player 2"),
                PlayerHeuristic("Player 3"), PlayerHeuristic("Player 4"),
                PlayerHeuristic("Player 5")]

    game = Game(players, display_map=True) 

    try:
        game.gameplay_loop()
    except Exception as e:
        logging.error("An error occurred: %s", str(e))
        logging.error("Stack trace: %s", traceback.format_exc())
