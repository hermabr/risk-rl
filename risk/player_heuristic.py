from risk.country import *
from risk.player import Player
import logging

class PlayerHeuristic(Player):
    def process_cards_phase(self):
        options = self.get_trade_in_options()
        if options:
            logging.info(f"\x1b[1m\nCards Phase - {self}\x1b[0m")
            self.game.trade_in_cards(self, options[0])
    
    def process_draft_phase(self):
        logging.info(f"\x1b[1m\nDraft Phase - {self}\x1b[0m")
        logging.info(f"\x1b[33mUnassigned soldiers: {self.unassigned_soldiers}\x1b[0m")
        while self.unassigned_soldiers > 0:
            player_state = self.game.get_player_army_summary(self)
            country_selected = player_state[0][0] # country with highest threat ratio
            # assign one soldier to country before we re-evaluate the threat ratios
            self.game.assign_soldiers(self, country_selected, 1)

    def process_attack_phase(self):
        logging.info(f"\x1b[1m\nAttack Phase - {self}\x1b[0m")
        max_attacks_per_round = 6 # maybe change this as game progresses?
        for attack_iter in range(max_attacks_per_round):
            attack_options = self.game.get_attack_options(self)
            if len(attack_options) == 0:
                return
            
            selected_attack = attack_options[0]
            attacker_country, attacker_country_n_soldiers = selected_attack[0]
            defender_country, defender_country_n_soldiers = selected_attack[1]

            if defender_country_n_soldiers > attacker_country_n_soldiers and attack_iter > 1:
                return

            attacking_soldiers = min(3, attacker_country_n_soldiers-1)
            self.game.attack(self, attacker_country, defender_country, attacking_soldiers)

    def process_fortify_phase(self):
        logging.info(f"\x1b[1m\nFortify Phase - {self}\x1b[0m")
        destination_countries = set()
        while True:
            fortify_options_ranked = self.game.get_fortify_options(self)
            if len(fortify_options_ranked) == 0:
                break

            origin, dest, *_ = fortify_options_ranked[0]
            if origin in destination_countries:
                break

            self.game.fortify(self, origin, dest, 1)
            destination_countries.add(dest)

        self.game.reinforce(self)
