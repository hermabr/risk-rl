import random
import networkx as nx
from risk.country import *
from risk.army import Army
from risk.player import Player
from risk.game_map import GameMap
from risk.card import *
import logging
import time


class GamePlayState(Enum):
    CARDS = 0
    DRAFT = 1
    ATTACK = 2
    FORTIFY = 3

class Game:
    def __init__(self, players, delay=True):
        self.delay = delay
        self.players = players
        for player in players:
            player.game = self
        self.game_map = GameMap()
        self.num_players = len(self.players)
        self.used_cards = []
        self.country_conquered_in_round = False
        self.current_phase = GamePlayState(0)
        self.current_player = players[0]
        self.assign_countries_and_initialize_armies()
        self.card_deck = init_deck()
        self.visualize()

    def gameplay_loop(self):
        logging.info('\x1b[1m\x1b[32mGame Started!\x1b[0m')
        while True:
            if self.num_players == 1:
                logging.info(f"\n\x1b[1m\x1b[32mGame won by player: {self.current_player}\x1b[0m")
                return

            if self.delay:
                time.sleep(0.25) # to see visualization of fully simulated games

            match self.current_phase:
                case GamePlayState.CARDS:
                    self.current_player.process_cards_phase()
                case GamePlayState.DRAFT:
                    self.current_player.process_draft_phase()
                case GamePlayState.ATTACK:
                    self.current_player.process_attack_phase()
                case GamePlayState.FORTIFY:
                    self.current_player.process_fortify_phase()
                case _:
                    raise ValueError(f"Invalid phase {self.curr_phase}")
            self.next_phase()

    def next_player(self):
        self.current_player = self.players[(self.players.index(self.current_player) + 1) % self.num_players]
        self.country_conquered_in_round = False

    def next_phase(self):
        if self.current_phase.value == len(GamePlayState) - 1:
            self.next_player()
        self.current_phase = GamePlayState((self.current_phase.value + 1) % len(GamePlayState))

    def visualize(self):
        self.game_map.draw_map()

    def assign_countries_and_initialize_armies(self):
        initial_armies_per_player_dict = {2: 40, 3: 35, 4: 30, 5: 25, 6: 20}
        countries = COUNTRIES
        random.shuffle(countries)
        num_players = self.num_players
        initial_armies_per_player = initial_armies_per_player_dict[num_players]

        for i, country in enumerate(countries):
            player = self.players[i % num_players]
            country.owner = player
            player.add_country(country)
            country.army = Army(player, 1)

        for player in self.players:
            territories_owned = player.countries
            num_territories = len(territories_owned)
            armies_to_assign = initial_armies_per_player - num_territories

            armies_distribution = [0] * num_territories
            for _ in range(armies_to_assign):
                idx = random.randint(0, num_territories - 1)
                armies_distribution[idx] += 1

            for idx, country in enumerate(territories_owned):
                country.army.n_soldiers += armies_distribution[idx]

    def reinforce(self, player: Player):
        reinforcements = max(len(player.countries) // 3, 3)

        for continent in CONTINENTS:
            if all([country.army and country.army.owner == player for country in continent.countries]):
                reinforcements += continent.extra_points

        player.unassigned_soldiers += reinforcements
        logging.info(f"\x1b[36m{player}\x1b[0m receives \x1b[33m{reinforcements}\x1b[0m reinforcements\n")

    def get_player_army_summary(self, player):
        summary = [
            (
                c,
                c.army.n_soldiers,
                [(n, n.army.n_soldiers) for n in self.game_map.neighbors(c) if n not in player.countries],
                sum(n.army.n_soldiers for n in self.game_map.neighbors(c) if n not in player.countries) / c.army.n_soldiers # border threat ratio
            )
            for c in player.countries
        ]
        summary.sort(key=lambda x: x[3], reverse=True)
        return [(c[0], c[1], c[2]) for c in summary]

    
    def assign_soldiers(self, player: Player, country: Country, n_soldiers: int):
        assert self.current_player == player
        assert n_soldiers <= player.unassigned_soldiers
        assert country in player.countries

        logging.info(f"\x1b[36m{player}\x1b[0m assigns \x1b[33m{n_soldiers}\x1b[0m soldiers to \x1b[35m{country}\x1b[0m")
        country_idx = player.countries.index(country)
        player.countries[country_idx].army.n_soldiers += n_soldiers
        player.unassigned_soldiers -= n_soldiers
        self.visualize()

    def get_attack_options(self, player):
        options = []
        for country in player.countries:
            if country.army.n_soldiers == 1:
                continue
            for neighbor in self.game_map.neighbors(country):
                if neighbor not in player.countries:
                    continent = neighbor.continent
                    remaining_enemy_countries = [
                        c for c in continent.countries if c.owner != player and c != neighbor
                    ]
                    troop_difference = country.army.n_soldiers - neighbor.army.n_soldiers

                    # can secure an continent with an attack where there is a troop advantage
                    will_secure_continent = len(remaining_enemy_countries) == 0 and troop_difference > 0
                    options.append(
                        ((country, country.army.n_soldiers), (neighbor, neighbor.army.n_soldiers), will_secure_continent, troop_difference)
                    )
        
        options.sort(key=lambda x: (x[2], x[3]), reverse=True) # prioritize oppotunity to secure continent first
        return [((from_country, from_soldiers), (to_country, to_soldiers)) for ((from_country, from_soldiers), (to_country, to_soldiers), _, _) in options]

    def attack(self, attacker: Player, attacker_country: Country, defender_country: Country, attacking_soldiers:int):
        assert self.current_player == attacker

        assert attacker_country in attacker.countries
        assert defender_country not in attacker.countries

        assert 1 <= attacking_soldiers <= 3
        assert 1 <= attacking_soldiers <= min(3, attacker_country.army.n_soldiers - 1)

        assert self.game_map.has_edge(attacker_country, defender_country)
        attack_successful = self.battle(attacker_country, defender_country, attacking_soldiers)

        if attack_successful and not self.country_conquered_in_round:
            self.draw_card(attacker)
            self.country_conquered_in_round = True
        
        self.visualize()

    @staticmethod
    def roll_dice(n):
        return sorted([random.randint(1, 6) for _ in range(n)], reverse=True)

    # return True/False battle won
    def battle(self, attacker_country: Country, defender_country: Country, attacking_soldiers: int):
        logging.info(f"\n\x1b[34mBattle: \x1b[31m{attacker_country}\x1b[34m -> \x1b[32m{defender_country}\x1b[34m, attacking soldiers\x1b[0m: {attacking_soldiers}")

        attacker = attacker_country.army
        defender = defender_country.army

        attack_rolls = self.roll_dice(attacking_soldiers)
        defend_rolls = self.roll_dice(min(2, defender.n_soldiers))

        logging.info(f"\x1b[31mAttacker rolls\x1b[0m: {attack_rolls}")
        logging.info(f"\x1b[32mDefender rolls\x1b[0m: {defend_rolls}")

        attacker_loss = 0
        defender_loss = 0
        for a, d in zip(attack_rolls, defend_rolls):
            if a > d:
                defender_loss += 1
            else:
                attacker_loss += 1

        attacker.n_soldiers -= attacker_loss
        defender.n_soldiers -= defender_loss

        logging.info(f"\x1b[32mDefender loses \x1b[33m{defender_loss}\x1b[0m\x1b[32m soldiers\x1b[0m")
        logging.info(f"\x1b[31mAttacker loses \x1b[33m{attacker_loss}\x1b[0m\x1b[31m soldiers\x1b[0m")

        if defender.n_soldiers <= 0:
            logging.info(f"\x1b[1m\x1b[31m{defender_country} has been conquered!\x1b[0m")
            defender_country.owner.remove_country(defender_country)

            if len(defender_country.owner.countries) == 0:
                eliminated_player = defender_country.owner
                eliminated_player_idx = self.players.index(eliminated_player)
                self.players.pop(eliminated_player_idx)
                self.num_players -= 1

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
        player_subgraph = self.game_map.get_subgraph(player.countries)
        ranked_options = []

        for component in nx.connected_components(player_subgraph):
            component_countries = list(component)
            for origin_country in component_countries:
                if origin_country.army.n_soldiers < 2:
                    continue
                
                for dest_country in component_countries:
                    if dest_country == origin_country:
                        continue
                    
                    neighbors = self.game_map.neighbors(dest_country)
                    enemy_neighbors = [n for n in neighbors if n.owner != player]
                    if enemy_neighbors:
                        troop_diff = min(dest_country.army.n_soldiers - n.army.n_soldiers for n in enemy_neighbors)
                    else:
                        troop_diff = float('inf')
                    
                    ranked_options.append((
                        origin_country,
                        dest_country,
                        troop_diff,
                        dest_country.army.n_soldiers,
                        origin_country.army.n_soldiers
                    ))

        ranked_options.sort(key=lambda x: (x[2], x[3], -x[4]))
        return ranked_options
 
    def fortify(self, player: Player, origin_country: Country, dest_country: Country, n_soldiers_move: int):
        assert self.current_player == player
        
        assert origin_country in player.countries
        assert dest_country in player.countries

        assert n_soldiers_move <= origin_country.army.n_soldiers

        fortify_options = self.get_fortify_options(player)
        origin_options = [x[0] for x in fortify_options]
        dest_options = [x[1] for x in fortify_options]

        assert origin_country in origin_options
        assert dest_country in dest_options
        
        logging.info(f"\x1b[36m{player}\x1b[0m fortifies \x1b[33m{n_soldiers_move}\x1b[0m from \x1b[35m{origin_country}\x1b[0m to \x1b[35m{dest_country}\x1b[0m")
        dest_country.army.n_soldiers += n_soldiers_move
        origin_country.army.n_soldiers -= n_soldiers_move
        self.visualize()
        
    def draw_card(self, player: Player):
        assert self.current_player == player

        if len(self.card_deck) == 0:
            self.card_deck = self.used_cards
            self.used_cards = []
            random.shuffle(self.card_deck)
        
        drawn_card = self.card_deck.pop()
        player.cards[drawn_card.card_type].append(drawn_card)

    def trade_in_cards(self, player: Player, card_combination):
        assert self.current_player == player
        
        trade_in_options = player.get_trade_in_options()
        assert card_combination in trade_in_options

        player.n_card_trade_ins += 1
        player.unassigned_soldiers += trade_in_rewards(player.n_card_trade_ins)

        cards_played = []
        for card in card_combination:
            cards_played.append(player.cards[card.card_type].pop())
        
        
        cards_str = ', '.join([str(x) for x in card_combination])
        logging.info(f"\x1b[36m{player}\x1b[0m plays cards: \x1b[33m ({cards_str})\x1b[0m")
        self.used_cards += cards_played
