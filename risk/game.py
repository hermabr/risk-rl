import random
import networkx as nx
from risk.country import *
from risk.army import Army
from risk.player import Player
from risk.game_map import GameMap
from risk.continent import CONTINENTS
# TODO add option to surpress prints, default False

class Game:
    def __init__(self, players):
        self.players = players
        self.countries = [Alaska, Alberta, CentralAmerica, EasternUS, Greenland, NorthwestTerritory, Ontario, Quebec, WesternUS, Venezuela, Brazil, Peru, Argentina, Iceland, GreatBritain, NorthernEurope, Scandinavia, Ukraine, SouthernEurope, WesternEurope, NorthAfrica, Egypt, EastAfrica, Congo, SouthAfrica, Madagascar, Afghanistan, China, India, Irkutsk, Japan, Kamchatka, MiddleEast, Mongolia, Siam, Siberia, Ural, Yakutsk, Indonesia, NewGuinea, WesternAustralia, EasternAustralia]
        self.game_map = GameMap()
        self.assign_countries()
        self.initialize_armies()
        self.num_players = len(self.players)
        self.curr_player = 0
    
    def next_player(self):
        if self.curr_player < self.num_players - 1:
            self.curr_player += 1
        else:
            self.curr_player = 0

    def assign_countries(self):
        random.shuffle(self.countries)
        for i, country in enumerate(self.countries):
            player = self.players[i % len(self.players)]
            country.owner = player
            player.add_country(country)
            self.game_map.add_node(country)

    def initialize_armies(self):
        for player in self.players:
            for country in player.countries:
                country.army = Army(player, 1)

    def visualize(self):
        self.game_map.draw_map()

    def reinforce(self, player: Player):
        reinforcements = max(len(player.countries) // 3, 3)

        for continent in CONTINENTS:
            if all([country.army and country.army.owner == player for country in continent.countries]):
                reinforcements += continent.extra_points
        
        player.unassigned_soldiers += reinforcements
        print(f"{player} receives {reinforcements} reinforcements.")
    
    def assign_soldiers(self, player: Player, country: Country, n_soldiers: int):
        assert self.players[self.curr_player] == player
        assert n_soldiers <= player.unassigned_soldiers
        assert country in player.countries
        #player.print_summary()

        contry_idx = player.index(country)
        player.countries[contry_idx].army.n_soldiers += n_soldiers
        player.unassigned_soldiers -= n_soldiers
        
        """
        # TODO move this into api, do not depend on io
        while reinforcements > 0:
            print(f"You have {reinforcements} soldiers to place.")
            for i, country in enumerate(player.countries):
                print(f"{i + 1}: {country} (Current soldiers: {country.soldiers.number})")

            choice = int(input("Choose a country to place a soldier (enter number): ")) - 1
            selected_country = player.countries[choice]
            selected_country.soldiers.number += 1
            reinforcements -= 1
        """
        
    def attack(self, attacker: Player, attacker_country: Country, defender_country: Country, attacking_soldiers:int):
        assert self.players[self.curr_player] == attacker
        
        assert attacker_country in attacker.countries
        assert defender_country not in attacker.countries
        
        assert 1 <= attacking_soldiers <= 3
        assert attacking_soldiers < attacker.number

        assert self.game_map.has_edge(attacker_country, defender_country)
        self.battle(attacker_country, defender_country, attacking_soldiers)

    @staticmethod
    def roll_dice(n):
        return sorted([random.randint(1, 6) for _ in range(n)], reverse=True)

    def battle(self, attacker_country: Country, defender_country: Country, attacking_soldiers: int):
        attacker = attacker_country.army
        defender = defender_country.army

        assert 1 <= attacking_soldiers <= 3
        assert attacking_soldiers < attacker.n_soldiers

        attack_rolls = self.roll_dice(min(3, attacker.n_soldiers - 1))
        defend_rolls = self.roll_dice(min(2, defender.n_soldiers, attack_rolls))

        print(f"Attacker rolls: {attack_rolls}")
        print(f"Defender rolls: {defend_rolls}")

        attacker_loss = 0
        defender_loss = 0
        for a, d in zip(attack_rolls, defend_rolls):
            if a > d:
                defender_loss += 1
            else:
                attacker_loss += 1
        
        defender_loss = min(defender_loss, defender.n_soldiers)
        defender.n_soldiers -= defender_loss
        attacker.n_soldiers -= attacker_loss
        
        print(f'Defender loses {defender_loss} soldiers')
        print(f'Attacker loses {attacker_loss} soldiers')

        if defender.number == 0:
            print(f"{defender_country} has been conquered!")
            defender_country.owner.remove_country(defender_country)
            defender_country.owner = attacker_country.owner

            defender_country.army.n_soldiers = 1 # init new country with an army of one
            attacker_country.owner.add_country(defender_country)
            attacker.n_soldiers -= 1

    # for each country that a player owns(player.countries)
    # get all other connected countries that the player owns
    # two countries are connected if there is a path between them
    # and all countries along that path are owned by the player
    def get_connected_countries(self, player: Player):
        country_connections = {country: [] for country in player.countries}

        player_countries = player.countries
        player_subgraph = self.game_map.subgraph(player_countries)

        connected_components = nx.connected_components(player_subgraph)
        for component in connected_components:
            component_countries = list(component)

            for country in component_countries:
                other_countries = [c for c in component_countries if c != country]
                country_connections[country] = other_countries

        return country_connections

        
    def fortify(self, player: Player, origin_country: Country, dest_country: Country, n_soldiers_move: int):
        assert self.players[self.curr_player] == player
        
        assert origin_country in player.countries
        assert dest_country in player.countries

        assert n_soldiers_move <= origin_country.army.n_soldiers
        
        connected_countries = self.get_connected_countries(player)
        assert dest_country in connected_countries[origin_country]

        dest_country.army.n_soldiers += n_soldiers_move
        origin_country.arny.n_soldiers -+ n_soldiers_move 

    def fortify_old(self, player: Player):
        assert self.players[self.curr_player] == player

        # make this not take io-actions
        print("Fortify phase: You can move soldiers between your countries.")
        print("Choose a country to move soldiers from:")
        for i, country in enumerate(player.countries):
            print(f"{i + 1}: {country} (Soldiers: {country.soldiers.number})")

        from_choice = int(input("Choose a country (enter number): ")) - 1
        from_country = player.countries[from_choice]

        if from_country.soldiers.number <= 1:
            print("Not enough soldiers to move.")
            return

        neighbors = [neighbor for neighbor in self.game_map.neighbors(from_country) if neighbor.owner == player]
        if not neighbors:
            print("No neighboring countries owned by you to fortify.")
            return

        print("Choose a neighboring country to move soldiers to:")
        for i, neighbor in enumerate(neighbors):
            print(f"{i + 1}: {neighbor} (Soldiers: {neighbor.soldiers.number})")

        to_choice = int(input("Choose a country (enter number): ")) - 1
        to_country = neighbors[to_choice]

        move_count = int(input(f"How many soldiers do you want to move? (Max: {from_country.soldiers.number - 1}): "))
        if move_count >= from_country.soldiers.number:
            print("Invalid number of soldiers.")
            return

        from_country.soldiers.number -= move_count
        to_country.soldiers.number += move_count
        print(f"Moved {move_count} soldiers from {from_country} to {to_country}.")
