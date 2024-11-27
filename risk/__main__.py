USE_LLM = True

if USE_LLM:
    import argparse
    import transformers
else:
    pass
from risk.game import Game
from risk.player_io import PlayerIO
from risk.player_heuristic import PlayerHeuristic
from risk.player_llm import PlayerLLM
import risk.logging_setup as logging_setup
import logging
import traceback

logging_setup.init_logging()

# +

if USE_LLM:
    default_model_path = "meta-llama/Llama-3.2-3B"
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--model_path", type=str, default=default_model_path)
        model_path = parser.parse_args().model_path
    except:
        model_path = default_model_path

    print(f"Using model: {model_path}")

    quantization_config = transformers.BitsAndBytesConfig(load_in_8bit=True)

    tokenizer = transformers.AutoTokenizer.from_pretrained(model_path)
    tokenizer.pad_token_id = tokenizer.eos_token_id

    model = transformers.AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        force_download=False,
        quantization_config=quantization_config
    )

    llm_number_tokens = {}
    for i in range(100):
        _, llm_number_tokens[i] = tokenizer(f"{i}")['input_ids']
else:
    pass

# +

players = [
    PlayerHeuristic("Player 1"),
    PlayerHeuristic("Player 2"),
    PlayerLLM("Player 3", model, tokenizer, llm_number_tokens) if USE_LLM else PlayerHeuristic("Player 3"),
    PlayerHeuristic("Player 4"),
    PlayerHeuristic("Player 5"),
]

game = Game(players, display_map=False, delay=False) 

def test_decode_attack_options(game: Game):
    for attack_options in range(game.total_attack_options_cnt):
        attack_country, defend_country, n_soldiers = game.decode_attack_option(attack_options)
        print(attack_country, defend_country, n_soldiers)

try:
    test_decode_attack_options(game)
    game.gameplay_loop()
except Exception as e:
    logging.error("An error occurred: %s", str(e))
    logging.error("Stack trace: %s", traceback.format_exc())
