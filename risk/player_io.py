from risk.country import *
from risk.player import Player

class PlayerIO(Player):
    def process_cards_phase(self):
        print(f"It is {self.name}'s turn\n")
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
        print("\nTroop draft phase")
        while self.unassigned_soldiers > 0:
            print(f"\nPlayer has {self.unassigned_soldiers} unassigned soldiers")
            position = self.game.get_player_army_summary(self)
            print("Current player position:")
            for i, x in enumerate(position):
                print(f"{i}: Territory: ({(x[0], x[1])}), Bordering Territories: {x[2]}")

            selected_country_idx = int(input("Select country(index) to assign troops: "))
            country = position[selected_country_idx][0]

            n_soldiers = int(input(f"Select number of soldiers to assign to the selected country: "))
            self.game.assign_soldiers(self, country, n_soldiers)
            self.game.visualize()

    def process_attack_phase(self):
        print("\nAttack phase")
        while True:
            attack_options = self.game.get_attack_options(self)

            print("\nAttack options:")
            for i, x in enumerate(attack_options):
                origin, dest = x
                print(f"{i}: {origin} -> {dest}")
            
            attack_selected = int(input("\nSelect attack option(or -1 to skip): "))
            if attack_selected == -1:
                break

            else:
                attacker_country, defender_country = [x[0] for x in attack_options[attack_selected]]
                n_soldiers = attacker_country.army.n_soldiers
                attacking_soldiers = int(input(f"Select number of soldiers(maximum {min(3, n_soldiers-1)}): "))
                self.game.attack(self, attacker_country, defender_country, attacking_soldiers)
    
                self.game.visualize()

    def process_fortify_phase(self):
        print("\nFortify phase")
        while True:
            fortify_options_ranked = self.game.get_fortify_options(self)

            print("\nFortify options (ranked):")
            for idx, (origin, dest, troop_diff, dest_army_size, origin_army_size) in enumerate(fortify_options_ranked):
                print(f"{idx}: Move from {origin.name} to {dest.name} | "
                      f"Dest Troop Diff: {troop_diff} | Dest Army Size: {dest_army_size} | Origin Army Size: {origin_army_size}")

            selected_option = int(input("\nSelect an option to fortify (or -1 to skip): "))
            if selected_option != -1:
                origin, dest, *_ = fortify_options_ranked[selected_option]
                max_soldiers = origin.army.n_soldiers - 1 
                n_soldiers_move = int(input(f"Select move (1 to {max_soldiers}): "))
                self.game.fortify(self, origin, dest, n_soldiers_move)
                self.game.visualize()
            else:
                print("No fortification option selected, moving to next phase")
                break
        
        self.game.reinforce(self)
