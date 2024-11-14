import random
import networkx as nx
from risk.country import *
from risk.soldier import Soldier
from risk.game_map import GameMap
from risk.continent import CONTINENTS

class Game:
    def __init__(self, players):
        self.players = players
        self.countries = [Alaska, Alberta, CentralAmerica, EasternUS, Greenland, NorthwestTerritory, Ontario, Quebec, WesternUS, Venezuela, Brazil, Peru, Argentina, Iceland, GreatBritain, NorthernEurope, Scandinavia, Ukraine, SouthernEurope, WesternEurope, NorthAfrica, Egypt, EastAfrica, Congo, SouthAfrica, Madagascar, Afghanistan, China, India, Irkutsk, Japan, Kamchatka, MiddleEast, Mongolia, Siam, Siberia, Ural, Yakutsk, Indonesia, NewGuinea, WesternAustralia, EasternAustralia]
        self.game_map = GameMap()
        self.assign_countries()
        self.initialize_soldiers()

    def assign_countries(self):
        random.shuffle(self.countries)
        for i, country in enumerate(self.countries):
            player = self.players[i % len(self.players)]
            country.owner = player
            player.add_country(country)
            self.game_map.add_node(country)

    def initialize_soldiers(self):
        for player in self.players:
            for country in player.countries:
                country.soldiers = Soldier(country, player, 1)

    def visualize(self):
        self.game_map.draw_map()

    def reinforce(self, player):
        reinforcements = max(len(player.countries) // 3, 3)
        print(f"{player} receives {reinforcements} reinforcements.")

        for continent in CONTINENTS:
            if all([country.soldiers and country.soldiers.owner == player for country in continent.countries]):
                reinforcements += continent.extra_points

        while reinforcements > 0:
            print(f"You have {reinforcements} soldiers to place.")
            for i, country in enumerate(player.countries):
                print(f"{i + 1}: {country} (Current soldiers: {country.soldiers.number})")

            choice = int(input("Choose a country to place a soldier (enter number): ")) - 1
            selected_country = player.countries[choice]
            selected_country.soldiers.number += 1
            reinforcements -= 1

    @staticmethod
    def roll_dice(n):
        return sorted([random.randint(1, 6) for _ in range(n)], reverse=True)

    def attack(self, attacker_country, defender_country, attacking_soldiers):
        attacker = attacker_country.soldiers
        defender = defender_country.soldiers

        assert 1 <= attacking_soldiers <= 3
        assert attacking_soldiers < attacker.number

        attack_rolls = self.roll_dice(min(3, attacker.number - 1))
        defend_rolls = self.roll_dice(min(2, defender.number, attack_rolls))

        print(f"Attacker rolls: {attack_rolls}")
        print(f"Defender rolls: {defend_rolls}")

        for a, d in zip(attack_rolls, defend_rolls):
            if a > d:
                defender.number -= 1
                print("Defender loses 1 soldier.")
            else:
                attacker.number -= 1
                print("Attacker loses 1 soldier.")

        if defender.number <= 0:
            print(f"{defender_country} has been conquered!")
            defender_country.owner.remove_country(defender_country)
            defender_country.owner = attacker_country.owner
            attacker_country.owner.add_country(defender_country)
            defender_country.soldiers = Soldier(defender_country, attacker_country.owner, 1)
            attacker.number -= 1

        def fortify(self, player):
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
