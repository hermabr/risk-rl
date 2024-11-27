from risk.country import *
from risk.player import Player
import logging
import time
import random

DELAY_TIME = 2 # seconds

class PlayerRandom(Player):
    def process_cards_phase(self):
        options = self.get_trade_in_options()
        if options:
            logging.info(f"\x1b[1m\nCards Phase - {self}\x1b[0m")
            self.game.trade_in_cards(self, random.choice(options))
    
    def process_draft_phase(self):
        logging.info(f"\x1b[1m\nDraft Phase - {self}\x1b[0m")
        logging.info(f"\x1b[33mUnassigned soldiers: {self.unassigned_soldiers}\x1b[0m")
        while self.unassigned_soldiers > 0:
            if self.game.delay:
                time.sleep(DELAY_TIME)

            country_selected = random.choice(self.game.get_player_army_summary(self))[0]
            soldiers_to_assign = random.randint(1, self.unassigned_soldiers)
            self.game.assign_soldiers(self, country_selected, soldiers_to_assign)

    def process_attack_phase(self):
        logging.info(f"\x1b[1m\nAttack Phase - {self}\x1b[0m")
        
        max_attacks_per_round = random.randint(0, 10)
        for _ in range(max_attacks_per_round):
            if self.game.delay:
                time.sleep(DELAY_TIME)

            attack_options = self.game.get_attack_options(self)
            if len(attack_options) == 0:
                return
            
            selected_attack = random.choice(attack_options)
            attacker_country, attacker_country_n_soldiers = selected_attack[0]
            defender_country, defender_country_n_soldiers = selected_attack[1]

            attacking_soldiers = random.randint(1, min(3, attacker_country_n_soldiers-1))
            self.game.attack(self, attacker_country, defender_country, attacking_soldiers)

    def process_fortify_phase(self):
        logging.info(f"\x1b[1m\nFortify Phase - {self}\x1b[0m")
        
        fortify_options = self.game.get_fortify_options(self)
        if fortify_options:
            origin, dest, _, _, origin_n_soldiers, _ = random.choice(fortify_options)
            n_soldiers_move = random.randint(1, origin_n_soldiers - 1)
            self.game.fortify(self, origin, dest, n_soldiers_move)

        self.game.reinforce(self)
