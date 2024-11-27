import time
import random
import logging
from tqdm.auto import tqdm
from collections import defaultdict
from risk.card import CardType
from risk.country import *
from risk.player import Player

DELAY_TIME = 2 # seconds

class PlayerLLM(Player):
    def __init__(self, name, model, tokenizer, llm_number_tokens):
        super().__init__(name)
        self.model = model
        self.tokenizer = tokenizer
        self.llm_number_tokens = llm_number_tokens
        self.current_seed = 0

    def _get_choice_probabilities(self, prompt, choices, NUM_SEEDS=5):
        if len(choices) == 2:
            NUM_SEEDS = min(NUM_SEEDS, 2)
        # we use num seeds to get a more stable estimate of the probabilities, since the llm is biased towards selecting the first option
        def get_raw_probabilities(prompt):
            tokenized_prompt = self.tokenizer(prompt, return_tensors="pt")
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
            assert out['scores'][-1].min() != float('-inf')
            probabilities = out['scores'][-1].softmax(dim=1)
            return probabilities

        final_probabilities = defaultdict(float)
        assert len(choices) <= 99

        for _ in tqdm(range(NUM_SEEDS), desc="choosing", leave=False):
            self.current_seed += 1
            random.seed(self.current_seed)
            choices = sorted(choices)
            random.shuffle(choices)
            prompt_with_choices = prompt + "\n\n" + "\n".join([f"{i+1}) {choice}" for i, choice in enumerate(choices)]) + "\n\nChoice: "

            probabilities = get_raw_probabilities(prompt_with_choices)

            total_probability_mass = 0

            for i in range(1, len(choices)+1):
                total_probability_mass += probabilities[0, self.llm_number_tokens[i]].item()

            assert total_probability_mass >= 0.5

            for i in range(1, len(choices)+1):
                #  print(f"{i}) {choices[i-1]}: {probabilities[0, all_number_tokens[i]].item()/total_probability_mass:.1%}")
                final_probabilities[choices[i-1]] += probabilities[0, self.llm_number_tokens[i]].item()/total_probability_mass / NUM_SEEDS

        #  return sorted(final_probabilities.items(), key=lambda x: -x[1])
        total_mass = sum(final_probabilities.values())
        assert abs(total_mass - 1) < 0.01

        choices, probabilities = zip(*final_probabilities.items())
        selected_choice = random.choices(choices, weights=probabilities, k=1)[0]

        return selected_choice

    def _get_textual_overview(self):
        game_state = "Regions:"
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
        from IPython.terminal.embed import embed
        embed(header="")
        input("Exit")
        print(f"It is {self.name}'s turn\n")
        logging.info(f"\x1b[1m\nCards Phase - {self}\x1b[0m")
        print(f"Cards on hand: {self.get_cards()}")

        options = self.get_trade_in_options()
        if options:
            print("Player has the following trade in options:")
            for i, x in enumerate(options):
                print(f"{i}: {x}")

            selected_option = int(input("Select option(or -1 to skip): "))
            if selected_option != -1:
                self.game.trade_in_cards(self, options[selected_option])
        else:
            print("Player cannot trade in any cards")

    def process_draft_phase(self):
        logging.info(f"\x1b[1m\nDraft Phase - {self}\x1b[0m")
        logging.info(f"\x1b[33mUnassigned soldiers: {self.unassigned_soldiers}\x1b[0m")

        while self.unassigned_soldiers > 0:
            text_state = self._get_textual_overview()
            text_state += f"\n{self.name} has {self.unassigned_soldiers} unassigned soldiers. Which of these territories would you like to assign the next soldier to?\n"
            position = self.game.get_player_army_summary(self)
            choices = []
            country_choices = []
            for x in position:
                choices += [f"Assign {x[1]} soldiers to {x[0].name}. Bordering Territories: {', '.join(f'{country.name}' for country,_ in x[2])}"]
                country_choices += [x[0]]
            choice = self._get_choice_probabilities(text_state, choices)
            selected_country = country_choices[choices.index(choice)]
            self.game.assign_soldiers(self, selected_country, 1)

    def process_attack_phase(self):
        logging.info(f"\x1b[1m\nAttack Phase - {self}\x1b[0m")

        total_solders_per_owner = defaultdict(int)
        for country in self.game.countries:
            total_solders_per_owner[country.owner.name] += country.army.n_soldiers
        print(sorted(total_solders_per_owner.items()))
        while True:
            text_state = self._get_textual_overview()
            text_state += "Attack options:\n"

            skip_or_attack_text = text_state

            attack_options = self.game.get_attack_options(self)

            attack_choices = []
            attack_defence_countries = []
            for x in attack_options:
                (origin_country, origin_soldiers), (dest_country, dest_soldiers) = x
                attack_choices += [f"{origin_country.name} ({origin_country.owner}) with {origin_soldiers} soldiers to attack {dest_country.name} ({dest_country.owner}) with {dest_soldiers} solders"]
                attack_defence_countries += [(origin_country, dest_country)]
            if len(attack_choices) == 0:
                break
            sorted_choices = sorted(attack_choices)
            random.shuffle(sorted_choices)
            skip_or_attack_text += "\n".join(sorted_choices)
            choice_probabilities = self._get_choice_probabilities(skip_or_attack_text, ["Skip","Attack"])
            if choice_probabilities == "Skip":
                break
            choice_probabilities = self._get_choice_probabilities(text_state, attack_choices)

            attacker_country, defender_country = attack_defence_countries[attack_choices.index(choice_probabilities)]

            n_soldiers = attacker_country.army.n_soldiers

            if n_soldiers-1 > 1:
                attacking_soldiers = int(self._get_choice_probabilities(self._get_textual_overview() + f"\n{self.name} (you) are using {attacker_country.name} with {attacker_country.army.n_soldiers} soldiers to attack {defender_country.name} with {defender_country.army.n_soldiers} soldiers", [f"Send {x+1} soldiers" for x in range(min(3, n_soldiers-1))]).split()[1])
            else:
                attacking_soldiers = 1

            logging.info(f"\x1b[33mLLM Attacking with {attacking_soldiers} soldiers from {attacker_country} to {defender_country}\x1b[0m")
            self.game.attack(self, attacker_country, defender_country, attacking_soldiers)

    def process_fortify_phase(self):
        logging.info(f"\x1b[1m\nFortify Phase - {self}\x1b[0m")
        max_fortify_rounds = len(self.game.get_fortify_options(self))*2
        for _ in range(max_fortify_rounds):
            self.game.get_fortify_options(self)
            text_state = self._get_textual_overview()
            text_state += "\nFortify options:\n"
            fortify_choices = []
            fortify_from_to = []
            for (origin_country, dest_country, origin_troop_diff, dest_troop_diff, origin_country.army.n_soldiers, dest_country.army.n_soldiers) in sorted(self.game.get_fortify_options(self)):
                fortify_choices += [f"Move soldiers from {origin_country.name} with {origin_country.army.n_soldiers} soldiers to {dest_country.name} with {dest_country.army.n_soldiers} soldier"]
                fortify_from_to += [(origin_country, dest_country)]
            skip_or_fortify_text = text_state + "\n".join(fortify_choices) + "\nDo we want to skip or fortify?"
            skip_or_fortify_choice = self._get_choice_probabilities(skip_or_fortify_text, ["Skip","Fortify"])
            if skip_or_fortify_choice == "Skip":
                break
            fortify_choice = self._get_choice_probabilities(text_state, fortify_choices)
            origin_country, dest_country = fortify_from_to[fortify_choices.index(fortify_choice)]
            number_of_soldiers_to_move = self._get_textual_overview() + f"\n{self.name} (you) are moving soldiers from {origin_country.name} with {origin_country.army.n_soldiers} soldiers to {dest_country.name} with {dest_country.army.n_soldiers} soldiers"
            if origin_country.army.n_soldiers > 1:
                number_of_soldiers_to_move = int(self._get_choice_probabilities(number_of_soldiers_to_move, [f"Move {x} soldiers" for x in range(1, origin_country.army.n_soldiers)]).split()[1])
            else:
                number_of_soldiers_to_move = 1
            logging.info(f"\x1b[33mLLM Fortifying {number_of_soldiers_to_move} soldiers from {origin_country} to {dest_country}\x1b[0m")
            self.game.fortify(self, origin_country, dest_country, number_of_soldiers_to_move)
        logging.info(f"\x1b[33mLLM Fortify phase ended\x1b[0m")
        self.game.reinforce(self)
