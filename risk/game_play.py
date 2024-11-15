from enum import Enum
from risk.game import Game
from risk.country import *
from risk.player import Player

class GamePlayState(Enum):
    CARDS = 0
    DRAFT = 1
    ATTACK = 2
    FORTIFY = 3

class GamePlay:
    def __init__(self, n_players=3):
        self.game = Game([Player(f'Player {i+1}') for i in range(n_players)])
        self.game.visualize()
        self.curr_phase = GamePlayState.CARDS
        self.curr_player_idx = self.game.curr_player
        self.curr_player = self.game.players[self.curr_player_idx]
        self.phase_map = {
            GamePlayState.CARDS: self.process_cards_phase,
            GamePlayState.DRAFT: self.process_draft_phase,
            GamePlayState.ATTACK: self.process_attack_phase,
            GamePlayState.FORTIFY: self.process_fortify_phase
        }
    
    def next_phase(self):
        self.curr_phase = GamePlayState((self.curr_phase.value + 1) % len(GamePlayState))
    
    def process_cards_phase(self):
        print(f"It is {self.curr_player}'s turn")
        print(f"Cards on hand: {self.curr_player.get_cards()}")

        options = self.curr_player.get_trade_in_options()
        if options:
            print("Player has the following trade in options:")
            for i, x in enumerate(options):
                print(f"{i}: {x}")
            
            selected_option = int(input("Select option(or -1 to skip): "))
            if selected_option != -1:
                self.game.trade_in_cards(self.curr_player, options[selected_option])
        else:
            print("Player cannot trade in any cards")
        
        self.next_phase()
    
    def process_draft_phase(self):
        print("\nTroop draft phase")
        while self.curr_player.unassigned_soldiers > 0:
            print(f"\nPlayer has {self.curr_player.unassigned_soldiers} unassigned soldiers")
            position = self.game.get_player_army_summary(self.curr_player)
            print("Current player position:")
            for i, x in enumerate(position):
                print(f"{i}: Territory: ({(x[0], x[1])}), Bordering Territories: {x[2]}")

            selected_country_idx = int(input("Select country(index) to assign troops: "))
            country = position[selected_country_idx][0]

            n_soldiers = int(input(f"Select number of soldiers to assign to the selected country: "))
            self.game.assign_soldiers(self.curr_player, country, n_soldiers)
            self.game.visualize()

        self.next_phase()

    def process_attack_phase(self):
        print("\nAttack phase")
        while True:
            attack_options = self.game.get_attack_options(self.curr_player)

            print("Attack options:")
            for i, x in enumerate(attack_options):
                origin, dest = x
                print(f"{i}: {origin} -> {dest}")
            
            attack_selected = int(input("Select attack option(or -1 to skip): "))
            if attack_selected == -1:
                break

            else:
                attacker_country, defender_country = [x[0] for x in attack_options[attack_selected]]
                n_soldiers = attacker_country.army.n_soldiers
                attacking_soldiers = int(input(f"Select number of soldiers(maximum {min(3, n_soldiers-1)}): "))
                self.game.attack(self.curr_player, attacker_country, defender_country, attacking_soldiers)
    
                self.game.visualize()
        
        self.next_phase()

    def rank_fortify_options(self, fortify_options):
        dest_countries = set(dest for _, dest in fortify_options)
        curr_player = self.curr_player

        dest_country_info = {
            dest_country: {
                'army_size': dest_country.army.n_soldiers,
                'troop_diff': float('inf') 
            }
            for dest_country in dest_countries
        }

        for dest_country in dest_countries:
            neighbors = self.game.game_map.neighbors(dest_country)
            enemy_neighbors = [n for n in neighbors if n.owner != curr_player]
            if enemy_neighbors:
                min_troop_diff = min(dest_country.army.n_soldiers - n.army.n_soldiers for n in enemy_neighbors)
                dest_country_info[dest_country]['troop_diff'] = min_troop_diff

        ranked_options = []
        for origin_country, dest_country in fortify_options:
            info = dest_country_info[dest_country]
            troop_diff = info['troop_diff']
            army_size = info['army_size']
            ranked_options.append((origin_country, dest_country, troop_diff, army_size, origin_country.army.n_soldiers))

        ranked_options.sort(key=lambda x: (x[2], x[3], -x[4]))
        return ranked_options

    def process_fortify_phase(self):
        while True:
            fortify_options_dict = self.game.get_fortify_options(self.curr_player)
            fortify_options = [(origin, dest) for origin, dests in fortify_options_dict.items() for dest in dests]
            fortify_options_ranked = self.rank_fortify_options(fortify_options)

            print("Fortify options (ranked):")
            for idx, (origin, dest, troop_diff, dest_army_size, origin_army_size) in enumerate(fortify_options_ranked):
                print(f"{idx}: Move from {origin.name} to {dest.name} | "
                      f"Dest Troop Diff: {troop_diff} | Dest Army Size: {dest_army_size} | Origin Army Size: {origin_army_size}")

            selected_option = int(input("Select an option to fortify (or -1 to skip): "))
            if selected_option != -1:
                origin, dest, *_ = fortify_options_ranked[selected_option]
                max_soldiers = origin.army.n_soldiers - 1 
                n_soldiers_move = int(input(f"Select move (1 to {max_soldiers}): "))
                self.game.fortify(self.curr_player, origin, dest, n_soldiers_move)
                print(f"Moved {n_soldiers_move} soldiers from {origin.name} to {dest.name}.")
                self.game.visualize()
            else:
                print("No fortification option selected, moving to next phase")
                break
        
        self.game.reinforce(self.curr_player)
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

