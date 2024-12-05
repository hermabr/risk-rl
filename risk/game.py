import random
import networkx as nx
from risk.country import *
from risk.army import Army
from risk.player import Player
from risk.player_rl import PlayerRL
from risk.game_map import GameMap
from risk.card import *
import logging
import matplotlib.colors as mcolors
import numpy as np
import bisect

COLOR_PALETTE = list(mcolors.TABLEAU_COLORS.values()) + list(mcolors.CSS4_COLORS.values())

class GamePlayState(Enum):
    CARDS = 0
    DRAFT = 1
    ATTACK = 2
    FORTIFY = 3

# this ensures that each player has the same color on the map plot
# throughout the game
def assign_unique_colors(players: List[Player]) -> dict:
    color_mapping = {}
    for i, player in enumerate(players):
        color_mapping[player] = COLOR_PALETTE[i % len(COLOR_PALETTE)]
    return color_mapping

class Game:
    def __init__(self, players, display_map=True, log_all=True, eval_log=False, max_rounds=60):
        self.num_rounds_played = 0
        self.display_map = display_map
        self.log_all = log_all
        self.eval_log = eval_log
        self.max_rounds = max_rounds
        self.players = players
        for player in players:
            player.game = self
        
        self.players_eliminated = []
            
        player_colors = assign_unique_colors(self.players)
        self.game_map = GameMap(display_map=display_map, player_colors=player_colors)
        
        self.num_players = len(self.players)
        self.num_players_start = self.num_players
        
        if self.log_all:
            logging.info(f"\nStarted new game with {self.num_players_start} players\n")
        
        self.used_cards = []
        self.country_conquered_in_round = False
        self.current_phase = GamePlayState(0)
        self.current_player = players[0]
        self.assign_countries_and_initialize_armies()
        self.card_deck = init_deck()
        if self.display_map:
            self.visualize()
        
        # setup for game state encoding
        self.countries = sorted(COUNTRIES.copy())
        self.num_countries = len(self.countries)
        self.country_idx_map = {c:i for i,c in enumerate(self.countries)}
        self.edge_list = [(self.country_idx_map[u], self.country_idx_map[v]) for u, v in self.game_map.edges()]
        self.edge_list.sort(key = lambda x: (x[0], x[1]))
        src = [x[0] for x in self.edge_list]
        dst = [x[1] for x in self.edge_list]
        self.edge_list_array = np.array([src, dst])
        self.edge_list_idx_map = {x: i for i, x in enumerate(self.edge_list)}
        self.n_edges = len(self.edge_list)

        # setup for attack option encoding/decoding
        self.border_map = {c: list(self.game_map.neighbors(c)) for c in self.countries}
        offset = 0
        self.attack_options_offset_vals = []
        self.attack_options_offset_map = {}
        for k, v in self.border_map.items():
            self.attack_options_offset_map[k] = offset
            self.attack_options_offset_vals.append(offset)
            offset += 3*len(v)
         
        self.total_attack_options_cnt = offset + 1 # add skip action
        self.attack_options_offset_map_rev = {v: k for k, v in self.attack_options_offset_map.items()}
        self.action_lookup_table = self.get_attack_action_lookup()
    
    # node features for GNN
    def get_game_state_encoded(self, player: Player):
        # node features (per territory):
        # 0: player holds territory
        # 1: army size if player hold territory, default 0
        # 2: army size if player does not hold territory: default 0
        # 3: number of bordering territories if player holds territory, default 0
        # 4: average soldier diff if player holds territory, default 0
        # 5: min solider diff if player holds territory
        # 6: max soldier diff if player holds territory
        # 7: number of bordering territories if player not holds territory, default 0
        # 8: average soldier diff if player not holds territory, default 0
        # 9: min solider diff if player not holds territory
        # 10: max soldier diff if player not holds territory
        # 11: can attack territory
        # 12: game round number, standardized

        node_features = np.zeros((self.num_countries, 13))
        for country_idx, country in enumerate(self.countries):
            country_n_soldiers = country.army.n_soldiers
            country_owner = country.army.owner
            own_country = country.owner == player
            if own_country:
                node_features[country_idx, 0] = 1
                node_features[country_idx, 1] = country_n_soldiers
            else:
                node_features[country_idx, 2] = country_n_soldiers
            
            neighbors = set()
            for c in player.countries:
                neighbors.update(self.game_map.neighbors(c))
            can_attack = int(not own_country and country in neighbors)
            node_features[country_idx, 11] = can_attack
            
            soldier_diffs = [country_n_soldiers - c.army.n_soldiers 
                for c in self.game_map.neighbors(country)
                    if c not in country_owner.countries
                    ]
            
            if soldier_diffs:
                n_borders = len(soldier_diffs)
                avg_diff = np.mean(soldier_diffs)
                min_diff = min(soldier_diffs)
                max_diff = max(soldier_diffs)
                if own_country:
                    node_features[country_idx, 3:7] = [n_borders, avg_diff, min_diff, max_diff]
                else:
                    node_features[country_idx, 7:11] = [n_borders, avg_diff, min_diff, max_diff]
        
        # standardize features
        for idx in [1, 2, 4, 5, 6, 8, 9, 10]:
            max_val = node_features[:, idx].max()
            if max_val != 0:
                node_features[:, idx] = node_features[:, idx] / max_val
            else:
                node_features[:, idx] = 0
        
        node_features[:, 12] = self.num_rounds_played / self.max_rounds
        return node_features
                    
                                   
    def get_attack_options_encoded(self, player: Player):
        attack_options_array = np.zeros(self.total_attack_options_cnt)
        for country in player.countries:
            n_soldiers = country.army.n_soldiers
            if n_soldiers <= 1:
                continue
            
            country_offset = self.attack_options_offset_map[country]
            border_countries = self.border_map[country]
            for border_idx, border_country in enumerate(border_countries):
                if border_country not in player.countries:
                    max_attack_soldiers = min(3, n_soldiers - 1)
                    for num_attack_soldiers in range(1, max_attack_soldiers + 1):
                        idx = country_offset + 3 * border_idx + (num_attack_soldiers - 1)
                        attack_options_array[idx] = 1
    
        attack_options_array[-1] = 1  # skip option
    
        return attack_options_array


    def decode_attack_option(self, attack_option_idx):
        if attack_option_idx == self.total_attack_options_cnt - 1:
            return (-1, -1, 0)

        pos = bisect.bisect_right(self.attack_options_offset_vals, attack_option_idx)
        country_offset = self.attack_options_offset_vals[pos - 1]
        diff = attack_option_idx - country_offset
        bordering_country_idx = diff // 3
        n_soldiers = (diff % 3) + 1

        attack_country = self.attack_options_offset_map_rev[country_offset]
        defend_country = self.border_map[attack_country][bordering_country_idx]

        return attack_country, defend_country, n_soldiers

    def get_attack_action_lookup(self):
        lookup_table = []
        for i in range(self.total_attack_options_cnt):
            attack_country, defend_country, n_soldiers = self.decode_attack_option(i)
            lookup_table.append((
                -1 if attack_country == -1 else self.countries.index(attack_country), 
                -1 if defend_country == -1 else self.countries.index(defend_country),
                n_soldiers
            ))
        
        return lookup_table
    
    def gameplay_loop(self):
        while True:
            if self.num_rounds_played >= self.max_rounds:
                if self.eval_log or self.log_all:
                    logging.info(f"\x1b[1m\x1b[31mGame ends in tie, reached upper limit for number of rounds: {self.max_rounds}\x1b[0m")
                
                self.players_eliminated.extend(self.players) # add all remaining players to collect experiences for training
                return self.num_rounds_played, 0, 1

            if self.num_players == 1:
                if self.log_all or self.eval_log:
                    logging.info(f"\x1b[1m\x1b[32mGame won by player: {self.current_player} after {self.num_rounds_played} rounds\x1b[0m")
                
                rl_won = int(isinstance(self.players[0], PlayerRL))
                return self.num_rounds_played, rl_won, 0

            match self.current_phase:
                case GamePlayState.CARDS:
                    self.current_player.process_cards_phase()
                case GamePlayState.DRAFT:
                    self.current_player.process_draft_phase()
                case GamePlayState.ATTACK:
                    self.current_player.process_attack_phase()
                case GamePlayState.FORTIFY:
                    self.current_player.process_fortify_phase() 
            self.next_phase()
    
    def visualize(self):
        self.game_map.draw_map()

    def next_player(self):
        next_player_idx = (self.players.index(self.current_player) + 1) % self.num_players
        if next_player_idx == 0:
            self.num_rounds_played += 1
        self.current_player = self.players[next_player_idx]
        self.country_conquered_in_round = False

    def next_phase(self):
        if self.current_phase.value == len(GamePlayState) - 1:
            self.next_player()
        self.current_phase = GamePlayState((self.current_phase.value + 1) % len(GamePlayState))

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
        if self.log_all:
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

        if self.log_all:
            logging.info(f"\x1b[36m{player}\x1b[0m assigns \x1b[33m{n_soldiers}\x1b[0m soldiers to \x1b[35m{country}\x1b[0m")
        
        country_idx = player.countries.index(country)
        player.countries[country_idx].army.n_soldiers += n_soldiers
        player.unassigned_soldiers -= n_soldiers
        if self.display_map:
            self.visualize()

    def get_soldier_diffs(self, player):
        diffs = []
        for country in player.countries:
            n_soldiers = country.army.n_soldiers
            for neighbor in self.game_map.neighbors(country):
                if neighbor not in player.countries:
                    diffs.append(n_soldiers - neighbor.army.n_soldiers)
        
        return diffs

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
        attack_successful, reward = self.battle(attacker_country, defender_country, attacking_soldiers)

        if attack_successful and not self.country_conquered_in_round:
            self.draw_card(attacker)
            self.country_conquered_in_round = True
        
        if self.display_map:
            self.visualize()

        if isinstance(attacker, PlayerRL) and self.log_all:
            logging.info(f"Reward for this attack: {reward}")
        
        game_won = self.num_players == 1
        return reward, game_won

    @staticmethod
    def roll_dice(n):
        return sorted([random.randint(1, 6) for _ in range(n)], reverse=True)

    # return True/False battle won
    def battle(self, attacker_country: Country, defender_country: Country, attacking_soldiers: int):
        if self.log_all:
            logging.info(f"\n\x1b[34mBattle: \x1b[31m{attacker_country}\x1b[34m -> \x1b[32m{defender_country}\x1b[34m, attacking soldiers\x1b[0m: {attacking_soldiers}")

        prev_player_continents = self.get_player_continents(attacker_country.owner)
        
        attacker = attacker_country.army
        defender = defender_country.army

        attack_rolls = self.roll_dice(attacking_soldiers)
        defend_rolls = self.roll_dice(min(2, defender.n_soldiers))

        if self.log_all:
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

        reward = -0.5 * attacker_loss

        if self.log_all:
            logging.info(f"\x1b[32mDefender loses \x1b[33m{defender_loss}\x1b[0m\x1b[32m soldiers\x1b[0m")
            logging.info(f"\x1b[31mAttacker loses \x1b[33m{attacker_loss}\x1b[0m\x1b[31m soldiers\x1b[0m")

        if defender.n_soldiers <= 0:
            reward += 10
            if self.log_all:
                logging.info(f"\x1b[1m\x1b[31m{defender_country} has been conquered!\x1b[0m")
            defender_country.owner.remove_country(defender_country)

            if len(defender_country.owner.countries) == 0:
                reward += 100
                eliminated_player = defender_country.owner
                if self.log_all or (self.eval_log and isinstance(eliminated_player, PlayerRL)):
                    logging.info(f"{eliminated_player} has been eliminated after {self.num_rounds_played} rounds")

                self.players_eliminated.append(eliminated_player)
                eliminated_player_idx = self.players.index(eliminated_player)
                self.players.pop(eliminated_player_idx)
                self.num_players -= 1
                if self.num_players == 1:
                    reward += 10_000 # game won
                    self.players_eliminated.append(self.players[0]) # collect experiences of winner for training

            defender_country.owner = attacker_country.owner
            attacker_country.owner.add_country(defender_country)

            # Move soldiers into the conquered country
            soldiers_to_move = attacking_soldiers
            if attacker.n_soldiers - soldiers_to_move < 1:
                soldiers_to_move = attacker.n_soldiers - 1
            attacker.n_soldiers -= soldiers_to_move
            defender_country.army = Army(attacker.owner, soldiers_to_move)

            if self.get_player_continents(attacker_country.owner) != prev_player_continents:
                reward += 1000
            
            return True, reward

        reward -= 2 # unsuccessful attack
        return False, reward

    def get_player_continents(self, player):
        continents = []
        for continent in CONTINENTS:
            if all([country.army.owner == player for country in continent.countries]):
                continents.append(continent)

        return continents
                

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

                origin_neighbors = self.game_map.neighbors(origin_country)
                origin_enemy_neighbors = [n for n in origin_neighbors if n.owner != player]
                if origin_enemy_neighbors:
                    origin_troop_diff = min(origin_country.army.n_soldiers - n.army.n_soldiers for n in origin_enemy_neighbors)
                else:
                    origin_troop_diff = float('inf')
                
                for dest_country in component_countries:
                    if dest_country == origin_country:
                        continue
                    
                    dest_neighbors = self.game_map.neighbors(dest_country)
                    dest_enemy_neighbors = [n for n in dest_neighbors if n.owner != player]
                    if dest_enemy_neighbors:
                        dest_troop_diff = min(dest_country.army.n_soldiers - n.army.n_soldiers for n in dest_enemy_neighbors)
                    else:
                        dest_troop_diff = float('inf')
                    
                    ranked_options.append((
                        origin_country,
                        dest_country,
                        origin_troop_diff,
                        dest_troop_diff,
                        origin_country.army.n_soldiers,
                        dest_country.army.n_soldiers
                    ))

        ranked_options.sort(key=lambda x: (x[3], -x[5], -x[2], -x[4]))
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
        
        if self.log_all:
            logging.info(f"\x1b[36m{player}\x1b[0m fortifies \x1b[33m{n_soldiers_move}\x1b[0m from \x1b[35m{origin_country}\x1b[0m to \x1b[35m{dest_country}\x1b[0m")
        
        dest_country.army.n_soldiers += n_soldiers_move
        origin_country.army.n_soldiers -= n_soldiers_move
        
        if self.display_map:
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
        
        if self.log_all:
            cards_str = ', '.join([str(x) for x in card_combination])
            logging.info(f"\x1b[36m{player}\x1b[0m plays cards: \x1b[33m ({cards_str})\x1b[0m")
        
        self.used_cards += cards_played
