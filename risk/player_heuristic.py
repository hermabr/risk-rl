from risk.country import *
from risk.player import Player
import logging
import time

DELAY_TIME = 2 # seconds

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
            if self.game.delay:
                time.sleep(DELAY_TIME)

            player_state = self.game.get_player_army_summary(self)
            country_selected = player_state[0][0] # country with highest threat ratio
            # assign one soldier to country before we re-evaluate the threat ratios
            self.game.assign_soldiers(self, country_selected, 1)

    def process_attack_phase(self):
        logging.info(f"\x1b[1m\nAttack Phase - {self}\x1b[0m")
        
        max_attacks_per_round = 6 # maybe change this as game progresses?
        for attack_iter in range(max_attacks_per_round):
            if self.game.delay:
                time.sleep(DELAY_TIME)

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

    # this is just a basic heuristic, defining and coding a near optimal fortify strategy
    # would be difficult, but this is something
    def process_fortify_phase(self):
        logging.info(f"\x1b[1m\nFortify Phase - {self}\x1b[0m")
        
        destination_countries = set() # set of countries that have received fortify troops in this round
        max_fortify_moves = 10 # TODO: determine what is sensible here
        for fortify_iter in range(max_fortify_moves):

            if self.game.delay:
                time.sleep(DELAY_TIME)

            fortify_options_ranked = self.game.get_fortify_options(self)
            
            fortify_options_ranked = [x for x in fortify_options_ranked if x[0] not in destination_countries]
            if len(fortify_options_ranked) == 0:
                break

            origin, dest, \
                origin_troop_diff, dest_troop_diff, \
                origin_n_soldiers, dest_n_soldiers = fortify_options_ranked[0]
            
            if origin_troop_diff == float('inf'):
                n_soldiers_move = max(1, (origin_n_soldiers-1) // 2)
            else:
                n_soldiers_move = 1
            
            self.game.fortify(self, origin, dest, n_soldiers_move)
            destination_countries.add(dest)

        self.game.reinforce(self)
