import json
import time
import random
import logging
import pandas as pd
from tqdm.auto import tqdm
from collections import defaultdict
from risk.card import CardType
from risk.country import *
from risk.player import Player

class PlayerLLM(Player):
    def __init__(self, name, model, tokenizer, llm_number_tokens, log_file):
        super().__init__(name)
        self.model = model
        self.tokenizer = tokenizer
        self.llm_number_tokens = llm_number_tokens
        self.current_seed = 0
        self.log = []
        self.log_file = log_file

    def _get_game_state(self):
        """
        Provides a dictionary representation of the current game state for logging purposes.
        """
        game_state = {
            "player_name": self.name,
            "regions": [],
            "soldiers_per_player": defaultdict(int),
            "cards_on_hand": {
                "Infantry": self.get_cards().get(CardType.INFANTRY, 0),
                "Cavalry": self.get_cards().get(CardType.CAVALRY, 0),
                "Artillery": self.get_cards().get(CardType.ARTILLERY, 0),
            },
            "current_turn": self.name,
            "turn_number": self.game.turn_number,
        }

        # Populate regions
        for country in self.game.countries:
            country_info = {
                "country_name": country.name,
                "soldiers": country.army.n_soldiers,
                "owner": country.owner.name if country.owner else "Unowned"
            }
            game_state["regions"].append(country_info)
            if country.owner:
                game_state["soldiers_per_player"][country.owner.name] += country.army.n_soldiers

        # Convert defaultdict to a normal dict for serialization
        game_state["soldiers_per_player"] = dict(game_state["soldiers_per_player"])

        return game_state

    def _get_choice_probabilities(self, 
                                  prompt, 
                                  choices, 
                                  NUM_SEEDS=5, 
                                  decision_type="generic_decision", 
                                  game_state=None, 
                                  turn_number=None):
        """
        Compute the probabilities for each choice given the prompt by querying the LLM.
        Logs the decision details.
        """

        assert decision_type != "generic_decision"

        # If turn_number or game_state not provided, try retrieving from self.game
        if turn_number is None:
            turn_number = getattr(self.game, "turn_number", None)
        #  if game_state is None:
        #      game_state = self._get_textual_overview()
        game_state = self._get_game_state()

        if len(choices) == 2:
            NUM_SEEDS = min(NUM_SEEDS, 2)
        
        def get_raw_probabilities(prompt_text):
            tokenized_prompt = self.tokenizer(prompt_text, return_tensors="pt")
            input_ids = tokenized_prompt.input_ids.to(self.model.device)
            attention_mask = tokenized_prompt.attention_mask.to(self.model.device)

            out = self.model.generate(
                input_ids,
                attention_mask=attention_mask,
                max_new_tokens=1,
                temperature=1,
                return_dict_in_generate=True,
                output_scores=True,
                do_sample=False,
                top_p=None,
                pad_token_id=self.tokenizer.eos_token_id
            )
            probabilities = out['scores'][-1].softmax(dim=1)
            return probabilities

        final_probabilities = defaultdict(float)
        raw_seed_data = []

        for seed_index in tqdm(range(NUM_SEEDS), desc="choosing", leave=False):
            self.current_seed += 1
            random.seed(self.current_seed)
            if len(choices) == 2:
                if seed_index % 2 == 0:
                    shuffled_choices = choices[:]
                else:
                    shuffled_choices = choices[::-1]
            else:
                # Regular random shuffle for more than two choices
                shuffled_choices = sorted(choices[:])
                random.shuffle(shuffled_choices)

            # Truncate if too many choices
            truncated_choices = shuffled_choices
            if len(truncated_choices) >= 100:
                truncated_choices = truncated_choices[:99]

            prompt_with_choices = (prompt + "\n\n" 
                                   + "\n".join([f"{i+1}) {choice}" for i, choice in enumerate(truncated_choices)]) 
                                   + "\n\nChoice: ")

            probabilities = get_raw_probabilities(prompt_with_choices)

            total_probability_mass = 0
            for i in range(1, len(truncated_choices)+1):
                total_probability_mass += probabilities[0, self.llm_number_tokens[i]].item()

            assert total_probability_mass >= 0.5, "Total probability mass is unexpectedly low."

            seed_probabilities = {}
            for i in range(1, len(truncated_choices)+1):
                choice_prob = probabilities[0, self.llm_number_tokens[i]].item()/total_probability_mass
                final_probabilities[truncated_choices[i-1]] += choice_prob/NUM_SEEDS
                seed_probabilities[truncated_choices[i-1]] = choice_prob

            merged_seed_data = [
                (choice, seed_probabilities[choice]) for choice in truncated_choices
            ]

            raw_seed_data.append({
                "seed": self.current_seed,
                "shuffled_order_with_probabilities": merged_seed_data
            })

        total_mass = sum(final_probabilities.values())
        assert abs(total_mass - 1) < 0.01, "Probability mass should be close to 1 after normalization."

        final_choices, final_probs = zip(*final_probabilities.items())
        selected_choice = random.choices(final_choices, weights=final_probs, k=1)[0]

        # Log the decision
        log_entry = {
            "decision_type": decision_type,
            "prompt": prompt,
            "choices": list(final_choices),
            "probabilities": {c: p for c, p in final_probabilities.items()},
            "selected_choice": selected_choice,
            #  "turn_number": turn_number,
            "game_state": game_state,
            "NUM_SEEDS": NUM_SEEDS,
            "raw_seed_data": raw_seed_data
        }
        self.log.append(log_entry)
        pd.DataFrame(self.log).to_csv(self.log_file, index=False)

        return selected_choice

    def _get_textual_overview(self):
        game_state = f"You are an expert risk board game player and you are {self.name}.\n\nRegions:"
        total_solders_per_owner = defaultdict(int)
        for country in self.game.countries:
            game_state += f"{country.name}: {country.army.n_soldiers} soldiers owned by {country.owner}\n"
            total_solders_per_owner[country.owner.name] += country.army.n_soldiers
        game_state += "\nSolders per player:\n"
        for owner, total_soldiers in total_solders_per_owner.items():
            game_state += f"{owner}: {total_soldiers} soldiers\n"
        game_state += "\nCards on hand:\n"
        game_state += f"Infatry: {self.get_cards()[CardType.INFANTRY]} cards\n"
        game_state += f"Cavalry: {self.get_cards()[CardType.CAVALRY]} cards\n"
        game_state += f"Artillery: {self.get_cards()[CardType.ARTILLERY]} cards\n"
        game_state += f"\nCurrent turn: {self.name}\n"
        return game_state

    def process_cards_phase(self):
        logging.info(f"\x1b[1m\n{self.game.turn_number}) Cards Phase - {self}\x1b[0m")
        print(f"Cards on hand: {self.get_cards()}")

        while options := self.get_trade_in_options():
            text_state = self._get_textual_overview()
            choices = ["Swap in " + '+'.join([str(card) for card in option]) for option in options]

            choice_skip_swap_in = self._get_choice_probabilities(
                prompt=text_state + "Possible swap in options:\n" + "\n".join([f"{i+1}) {choice}" for i, choice in enumerate(choices)]) + "\nDo you want to swap in cards or skip?",
                choices=["Swap in", "Skip"],
                decision_type="cards_phase_swap_or_skip",
                game_state=text_state,
                turn_number=getattr(self.game, "turn_number", None)
            )
            if choice_skip_swap_in == "Skip":
                break

            if len(options) > 1:
                chosen_option_str = self._get_choice_probabilities(
                    prompt=text_state + "Which of these options do you want to swap in?\n",
                    choices=choices,
                    decision_type="cards_phase_which_swap_option",
                    game_state=text_state,
                    turn_number=getattr(self.game, "turn_number", None)
                )
            else:
                chosen_option_str = choices[0]

            chosen_option = options[choices.index(chosen_option_str)]
            self.game.trade_in_cards(self, chosen_option)
        else:
            print("Player cannot trade in any cards")

    def process_draft_phase(self):
        logging.info(f"\x1b[1m\n{self.game.turn_number}) Draft Phase - {self}\x1b[0m")
        logging.info(f"\x1b[33mUnassigned soldiers: {self.unassigned_soldiers}\x1b[0m")

        while self.unassigned_soldiers > 0:
            text_state = self._get_textual_overview()
            text_state += f"\n{self.name} has {self.unassigned_soldiers} unassigned soldiers. Which of these territories would you like to assign the next soldier to?\n"
            position = self.game.get_player_army_summary(self)
            choices = []
            country_choices = []
            for x in position:
                choices.append(f"Assign {x[1]} soldiers to {x[0].name}. Bordering Territories: {', '.join(f'{country.name}' for country,_ in x[2])}")
                country_choices.append(x[0])

            choice = self._get_choice_probabilities(
                prompt=text_state,
                choices=choices,
                decision_type="draft_phase_assign_soldier",
                game_state=text_state,
                turn_number=getattr(self.game, "turn_number", None)
            )
            selected_country = country_choices[choices.index(choice)]
            self.game.assign_soldiers(self, selected_country, 1)

    def process_attack_phase(self):
        logging.info(f"\x1b[1m\n{self.game.turn_number}) Attack Phase - {self}\x1b[0m")

        total_solders_per_owner = defaultdict(int)
        for country in self.game.countries:
            total_solders_per_owner[country.owner.name] += country.army.n_soldiers
        print(sorted(total_solders_per_owner.items()))

        while True:
            text_state = self._get_textual_overview()
            if not self.game.country_conquered_in_round:
                text_state += "\nNo countries were conquered in this round. Attack to get bonus.\n"
            else:
                text_state += "\nYou have already conquered a country this round.\n"
            text_state += "Attack options:\n"

            attack_options = self.game.get_attack_options(self)
            attack_choices = []
            attack_defence_countries = []
            for x in attack_options:
                (origin_country, origin_soldiers), (dest_country, dest_soldiers) = x
                attack_choices.append(
                    f"{origin_country.name} ({origin_country.owner}) with {origin_soldiers} soldiers to attack {dest_country.name} ({dest_country.owner}) with {dest_soldiers} soldiers"
                )
                attack_defence_countries.append((origin_country, dest_country))

            if len(attack_choices) == 0:
                break

            # Decide whether to skip attacking or proceed
            choice_skip_or_attack = self._get_choice_probabilities(
                prompt=text_state + "\n" + "\n".join(sorted(attack_choices)) + "\nDo you want to Skip or Attack?",
                choices=["Skip","Attack"],
                decision_type="attack_phase_skip_or_attack",
                game_state=text_state,
                turn_number=getattr(self.game, "turn_number", None)
            )
            if choice_skip_or_attack == "Skip":
                break

            # Which attack to perform
            chosen_attack = self._get_choice_probabilities(
                prompt=text_state,
                choices=attack_choices,
                decision_type="attack_phase_which_attack",
                game_state=text_state,
                turn_number=getattr(self.game, "turn_number", None)
            )

            attacker_country, defender_country = attack_defence_countries[attack_choices.index(chosen_attack)]
            n_soldiers = attacker_country.army.n_soldiers

            # Decide how many soldiers to send
            if n_soldiers - 1 > 1:
                num_soldier_choice = self._get_choice_probabilities(
                    prompt=self._get_textual_overview() + f"\n{self.name} (you) are using {attacker_country.name} with {attacker_country.army.n_soldiers} soldiers to attack {defender_country.name} with {defender_country.army.n_soldiers} soldiers",
                    choices=[f"Send {x+1} soldiers" for x in range(min(3, n_soldiers-1))],
                    decision_type="attack_phase_how_many_soldiers",
                    game_state=self._get_textual_overview(),
                    turn_number=getattr(self.game, "turn_number", None)
                )
                attacking_soldiers = int(num_soldier_choice.split()[1])
            else:
                attacking_soldiers = 1

            logging.info(f"\x1b[33mLLM Attacking with {attacking_soldiers} soldiers from {attacker_country} to {defender_country}\x1b[0m")
            self.game.attack(self, attacker_country, defender_country, attacking_soldiers)

    def process_fortify_phase(self):
        logging.info(f"\x1b[1m\n{self.game.turn_number}) Fortify Phase - {self}\x1b[0m")
        max_fortify_rounds = len(self.game.get_fortify_options(self))*2
        for _ in range(max_fortify_rounds):
            fortify_options = self.game.get_fortify_options(self)
            text_state = self._get_textual_overview()
            text_state += "\nFortify options:\n"
            fortify_choices = []
            fortify_from_to = []

            # Unpack the data from the fortify options
            for (origin_country, dest_country, _, _, _, _) in sorted(fortify_options, key=lambda x: x[0].name):
                fortify_choices.append(
                    f"Move soldiers from {origin_country.name} with {origin_country.army.n_soldiers} soldiers to {dest_country.name} with {dest_country.army.n_soldiers} soldiers"
                )
                fortify_from_to.append((origin_country, dest_country))

            if len(fortify_choices) == 0:
                break

            skip_or_fortify_choice = self._get_choice_probabilities(
                prompt=text_state + "\n".join(fortify_choices) + "\nDo we want to skip or fortify?",
                choices=["Skip","Fortify"],
                decision_type="fortify_phase_skip_or_fortify",
                game_state=text_state,
                turn_number=getattr(self.game, "turn_number", None)
            )
            if skip_or_fortify_choice == "Skip":
                break

            if len(fortify_choices) == 1:
                fortify_choice = fortify_choices[0]
            else:
                fortify_choice = self._get_choice_probabilities(
                    prompt=text_state,
                    choices=fortify_choices,
                    decision_type="fortify_phase_which_move",
                    game_state=text_state,
                    turn_number=getattr(self.game, "turn_number", None)
                )

            origin_country, dest_country = fortify_from_to[fortify_choices.index(fortify_choice)]
            move_prompt = (self._get_textual_overview() 
                           + f"\n{self.name} (you) are moving soldiers from {origin_country.name} with {origin_country.army.n_soldiers} soldiers to {dest_country.name} with {dest_country.army.n_soldiers} soldiers")

            if origin_country.army.n_soldiers > 1:
                number_of_soldiers_str = self._get_choice_probabilities(
                    prompt=move_prompt,
                    choices=[f"Move {x} soldiers" for x in range(1, origin_country.army.n_soldiers)],
                    decision_type="fortify_phase_how_many_soldiers",
                    game_state=self._get_textual_overview(),
                    turn_number=getattr(self.game, "turn_number", None)
                )
                number_of_soldiers_to_move = int(number_of_soldiers_str.split()[1])
            else:
                number_of_soldiers_to_move = 1

            logging.info(f"\x1b[33mLLM Fortifying {number_of_soldiers_to_move} soldiers from {origin_country} to {dest_country}\x1b[0m")
            self.game.fortify(self, origin_country, dest_country, number_of_soldiers_to_move)
        logging.info(f"\x1b[33mLLM Fortify phase ended\x1b[0m")
        self.game.reinforce(self)
