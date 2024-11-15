from risk.game import Game
from risk.country import *
from risk.player import Player

class GamePlay:
    def __init__(self, n_players=3):
        self.game = Game([Player(f'Player {i+1}') for i in range(n_players)])
        self.game.visualize()
        self.game_phases = ['cards', 'draft', 'attack', 'fortify'] # not used
        self.curr_phase = 0
        self.curr_player_idx = self.game.curr_player
        self.curr_player = self.game.players[self.curr_player_idx]
        self.phase_map = {
            0: self.process_cards_phase,
            1: self.process_draft_phase,
            2: self.process_attack_phase,
            3: self.process_fortify_phase
        }
    
    def next_phase(self):
        if self.curr_phase == 3:
            self.curr_phase = 0
        else:
            self.curr_phase += 1
    
    def process_cards_phase(self):
        print(f"It is {self.curr_player}'s turn")
        options = self.curr_player.get_trade_in_options()
        if options:
            print(f"Player has the following trade in options: {options}")
        else:
            print("Player cannot trade in any cards")
        self.next_phase()
    
    def process_draft_phase(self):
        self.next_phase()

    def process_attack_phase(self):
        while True:
            attack_options = self.game.get_attack_options(self.curr_player)
            attack_options.sort(key = lambda x: x[0].army.n_soldiers - x[1].army.n_soldiers, reverse=True)
            print(f"Attack options:\n {attack_options}")
            attack_selected = int(input("Select attack option: "))
            if attack_selected == -1:
                print('No attack selected, moving over to next phase')
                break

            else:
                attacker_country, defender_country = attack_options[attack_selected]
                n_soldiers = attacker_country.army.n_soldiers
                attacking_soldiers = int(input(f"Select number of soldiers(maximum {min(3, n_soldiers-1)}): "))

                self.game.attack(self.curr_player, attacker_country, defender_country, attacking_soldiers)
                self.game.visualize()
        
        self.next_phase()

    def process_fortify_phase(self):
        # TODO
        self.game.next_player()
        self.curr_player_idx = self.game.curr_player
        self.curr_player = self.game.players[self.curr_player_idx]
        self.next_phase()
    
    def gameplay_loop(self):
        print('Game Started!')
        while True:
            self.phase_map[self.curr_phase]()

if __name__ == '__main__':
    play = GamePlay()
    play.gameplay_loop()

