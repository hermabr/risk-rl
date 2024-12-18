import risk.logging_setup as logging_setup
import logging
import traceback
import risk.train_rl as training
import risk.play_game as play

# uncomment this to play a game
#play.play()

try:
    training.train(num_episodes=30_000, eval_interval=200) # play more games
    
    # test loading checkpoint
    #training.train(num_episodes=100, eval_interval=50, checkpoint_path='risk/model_checkpoints/rl_model_checkpoint_episode_100_2024_12_04_14_54.pt') # play more games
except Exception as e:
    logging.error("An error occurred: %s", str(e))
    logging.error("Stack trace: %s", traceback.format_exc())
