import risk.logging_setup as logging_setup
import logging
import traceback
import risk.train_rl as training
import risk.play_game as play

# uncomment this to play a game
#play.play()

logging_setup.init_logging("rl_training_log")
try:
    training.train(num_episodes=20_000) # play more games
except Exception as e:
    logging.error("An error occurred: %s", str(e))
    logging.error("Stack trace: %s", traceback.format_exc())
