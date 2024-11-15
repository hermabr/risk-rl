import random
import networkx as nx
from risk.country import *
from risk.army import Army
from risk.player import Player
from risk.game_map import GameMap
from risk.continent import CONTINENTS
from risk.card import *
import matplotlib.pyplot as plt

class Game:
    def __init__(self, players):
        self.players = players
        self.countries = [Alaska, Alberta, CentralAmerica, EasternUS, Greenland, NorthwestTerritory, Ontario, Quebec, WesternUS, Venezuela, Brazil, Peru, Argentina, Iceland, GreatBritain, NorthernEurope, Scandinavia, Ukraine, SouthernEurope, WesternEurope, NorthAfrica, Egypt, EastAfrica, Congo, SouthAfrica, Madagascar, Afghanistan, China, India, Irkutsk, Japan, Kamchatka, MiddleEast, Mongolia, Siam, Siberia, Ural, Yakutsk, Indonesia, NewGuinea, WesternAustralia, EasternAustralia]
        self.game_map = GameMap()
        self.assign_countries()
        self.initialize_armies()
        self.num_players = len(self.players)
        self.curr_player = 0
        self.card_deck = init_deck()
        self.used_cards = []
        self.country_conquered_in_round = False
    
    # TODO: should add some verification that the game flow is correct/ could keep track of last player
    # that got reinforcement and make sure that the next attacker/drafter is the player that is next in line
    
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

    def initialize_armies(self):
        for player in self.players:
            for country in player.countries:
                country.army = Army(player, random.randint(1,5)) # TODO change later

    def visualize(self):
        self.game_map.draw_map()

    def reinforce(self, player: Player):
        reinforcements = max(len(player.countries) // 3, 3)

        for continent in CONTINENTS:
            if all([country.army and country.army.owner == player for country in continent.countries]):
                reinforcements += continent.extra_points
        
        player.unassigned_soldiers += reinforcements
        print(f"{player} receives {reinforcements} reinforcements.")

    def get_player_army_summary(self, player):
        summary = [
            (
                c,
                c.army.n_soldiers,
                [(n, n.army.n_soldiers) for n in self.game_map.neighbors(c) if n not in player.countries]
            )
            for c in player.countries
        ]
        summary.sort(key=lambda x: (len(x[2]), x[1]), reverse=True) # this is not the final hueristic to use for ranking
        return summary

    
    def assign_soldiers(self, player: Player, country: Country, n_soldiers: int):
        assert self.players[self.curr_player] == player
        assert n_soldiers <= player.unassigned_soldiers
        assert country in player.countries

        country_idx = player.countries.index(country)
        player.countries[country_idx].army.n_soldiers += n_soldiers
        player.unassigned_soldiers -= n_soldiers

    def get_attack_options(self, player):
        options = [] # tuple ((country_from, n_soldiers), (country_to_attack, n_soldiers))
        for country in player.countries:
            if country.army.n_soldiers == 1:
                continue
            neighbor_countries = self.game_map.neighbors(country)
            for n in neighbor_countries:
                if n not in player.countries:
                    options.append(((country, country.army.n_soldiers), (n, n.army.n_soldiers)))
        
        options.sort(key=lambda x: x[0][1] - x[1][1], reverse=True)
        return options
        
    def attack(self, attacker: Player, attacker_country: Country, defender_country: Country, attacking_soldiers:int):
        assert self.players[self.curr_player] == attacker
        
        assert attacker_country in attacker.countries
        assert defender_country not in attacker.countries
        
        assert 1 <= attacking_soldiers <= 3
        assert 1 <= attacking_soldiers <= min(3, attacker_country.army.n_soldiers - 1)

        assert self.game_map.has_edge(attacker_country, defender_country)
        attack_successful = self.battle(attacker_country, defender_country, attacking_soldiers)
        
        if attack_successful and not self.country_conquered_in_round:
            self.draw_card(attacker)
            self.country_conquered_in_round = True

    @staticmethod
    def roll_dice(n):
        return sorted([random.randint(1, 6) for _ in range(n)], reverse=True)

    # return True/False battle won
    def battle(self, attacker_country: Country, defender_country: Country, attacking_soldiers: int):
        attacker = attacker_country.army
        defender = defender_country.army

        attack_rolls = self.roll_dice(attacking_soldiers)
        defend_rolls = self.roll_dice(min(2, defender.n_soldiers))

        print(f"Attacker rolls: {attack_rolls}")
        print(f"Defender rolls: {defend_rolls}")

        attacker_loss = 0
        defender_loss = 0
        for a, d in zip(attack_rolls, defend_rolls):
            if a > d:
                defender_loss += 1
            else:
                attacker_loss += 1

        attacker.n_soldiers -= attacker_loss
        defender.n_soldiers -= defender_loss

        print(f'Defender loses {defender_loss} soldiers')
        print(f'Attacker loses {attacker_loss} soldiers')

        if defender.n_soldiers <= 0:
            print(f"{defender_country} has been conquered!")
            defender_country.owner.remove_country(defender_country)
            defender_country.owner = attacker_country.owner
            attacker_country.owner.add_country(defender_country)

            # Move soldiers into the conquered country
            soldiers_to_move = attacking_soldiers
            if attacker.n_soldiers - soldiers_to_move < 1:
                soldiers_to_move = attacker.n_soldiers - 1
            attacker.n_soldiers -= soldiers_to_move
            defender_country.army = Army(attacker.owner, soldiers_to_move)
            return True

        return False


    # for each country that a player owns(player.countries)
    # get all other connected countries that the player owns
    # two countries are connected if there is a path between them
    # and all countries along that path are owned by the player
    def get_fortify_options(self, player: Player):
        player_countries = player.countries
        player_subgraph = self.game_map.subgraph(player_countries)
        fortify_options = {}

        connected_components = nx.connected_components(player_subgraph)
        for component in connected_components:
            component_countries = list(component)

            for country in component_countries:
                if country.army.n_soldiers < 2:
                    continue
                other_countries = [c for c in component_countries if c != country]
                fortify_options[country] = other_countries

        return fortify_options

        
    def fortify(self, player: Player, origin_country: Country, dest_country: Country, n_soldiers_move: int):
        assert self.players[self.curr_player] == player
        
        assert origin_country in player.countries
        assert dest_country in player.countries

        assert n_soldiers_move <= origin_country.army.n_soldiers

        fortify_options = self.get_fortify_options(player)
        assert origin_country in fortify_options.keys()
        assert dest_country in fortify_options[origin_country]
        
        dest_country.army.n_soldiers += n_soldiers_move
        origin_country.army.n_soldiers -= n_soldiers_move
        

    def draw_card(self, player: Player):
        assert self.players[self.curr_player] == player

        if len(self.card_deck) == 0:
            self.card_deck = self.used_cards
            self.used_cards = []
            random.shuffle(self.card_deck)
        
        drawn_card = self.card_deck.pop()
        player.cards[drawn_card.card_type].append(drawn_card)

    def trade_in_cards(self, player: Player, card_combination):
        assert self.players[self.curr_player] == player
        
        trade_in_options = player.get_trade_in_options()
        assert card_combination in trade_in_options

        player.n_card_trade_ins += 1
        player.unassigned_soldiers += trade_in_rewards(player.n_card_trade_ins)

        cards_played = []
        for card in card_combination:
            cards_played.append(player.cards[card.card_type].pop())

        self.used_cards += cards_played
