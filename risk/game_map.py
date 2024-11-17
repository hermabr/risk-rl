import networkx as nx
from typing import List

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
plt.ion()

import risk.country

class GameMap(nx.Graph):
    def __init__(self, display_map=True):
        super().__init__()
        self.initialize_game_map()
        self.positions = {
            risk.country.Alaska: (-2, 6),
            risk.country.NorthwestTerritory: (-1, 6),
            risk.country.Greenland: (1, 6),
            risk.country.Alberta: (-1.5, 5),
            risk.country.Ontario: (-0.5, 5),
            risk.country.Quebec: (0.5, 5),
            risk.country.WesternUS: (-1.5, 4),
            risk.country.EasternUS: (0, 4),
            risk.country.CentralAmerica: (-1, 3),
            risk.country.Venezuela: (-1, 2),
            risk.country.Brazil: (0, 1),
            risk.country.Peru: (-1, 1),
            risk.country.Argentina: (-1, 0),
            risk.country.Iceland: (1.5, 5),
            risk.country.GreatBritain: (2, 4.5),
            risk.country.Scandinavia: (3, 5),
            risk.country.NorthernEurope: (3, 4),
            risk.country.WesternEurope: (2, 3.5),
            risk.country.SouthernEurope: (3, 3),
            risk.country.Ukraine: (4, 4.5),
            risk.country.NorthAfrica: (1.5, 2),
            risk.country.Egypt: (3, 2),
            risk.country.EastAfrica: (3, 1),
            risk.country.Congo: (3, 0),
            risk.country.SouthAfrica: (3, -1),
            risk.country.Madagascar: (4, -1),
            risk.country.Ural: (5, 5),
            risk.country.Siberia: (6, 5.5),
            risk.country.Yakutsk: (7, 6),
            risk.country.Irkutsk: (7, 5),
            risk.country.Kamchatka: (8, 5.5),
            risk.country.Japan: (8, 4),
            risk.country.Mongolia: (7, 4),
            risk.country.China: (6, 4),
            risk.country.Afghanistan: (5, 4),
            risk.country.MiddleEast: (4, 3),
            risk.country.India: (5.5, 3),
            risk.country.Siam: (6.5, 3),
            risk.country.Indonesia: (7, 2),
            risk.country.NewGuinea: (8, 1.5),
            risk.country.WesternAustralia: (7, 1),
            risk.country.EasternAustralia: (8, 0.5)
        }
        if display_map:
            self.fig, self.ax = plt.subplots(figsize=(18, 10))
            plt.ion()

    def draw_map(self):
        self.ax.clear()
        color_map = []
        players = []
        for node in self.nodes():
            if node.army and node.army.owner:
                if node.army.owner not in players:
                    players.append(node.army.owner)

        players = sorted(players, key=lambda p: str(p))
        color_map = []
        for node in self.nodes():
            if node.army and node.army.owner:
                color_map.append(players.index(node.army.owner))
            else:
                color_map.append('gray')

        cmap = plt.cm.tab20
        nx.draw(
            self,
            with_labels=True,
            node_color=color_map,
            cmap=cmap,
            pos=self.positions,
            node_size=3000,
            ax=self.ax
        )

        legend_elements = []
        for i, player in enumerate(players):
            color = cmap(float(i) / max(len(players) - 1, 1))
            legend_elements.append(Patch(facecolor=color, edgecolor='black', label=str(player)))

        self.ax.legend(handles=legend_elements, title="Players", loc='best')
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def initialize_game_map(self):
        self.add_edge(risk.country.Alaska, risk.country.NorthwestTerritory)
        self.add_edge(risk.country.Alaska, risk.country.Alberta)
        self.add_edge(risk.country.NorthwestTerritory, risk.country.Alberta)
        self.add_edge(risk.country.NorthwestTerritory, risk.country.Ontario)
        self.add_edge(risk.country.NorthwestTerritory, risk.country.Greenland)
        self.add_edge(risk.country.Alberta, risk.country.Ontario)
        self.add_edge(risk.country.Alberta, risk.country.WesternUS)
        self.add_edge(risk.country.Ontario, risk.country.Quebec)
        self.add_edge(risk.country.Ontario, risk.country.EasternUS)
        self.add_edge(risk.country.Ontario, risk.country.WesternUS)
        self.add_edge(risk.country.Quebec, risk.country.EasternUS)
        self.add_edge(risk.country.Quebec, risk.country.Greenland)
        self.add_edge(risk.country.WesternUS, risk.country.EasternUS)
        self.add_edge(risk.country.WesternUS, risk.country.CentralAmerica)
        self.add_edge(risk.country.EasternUS, risk.country.CentralAmerica)
        self.add_edge(risk.country.Venezuela, risk.country.CentralAmerica)
        self.add_edge(risk.country.Venezuela, risk.country.Brazil)
        self.add_edge(risk.country.Venezuela, risk.country.Peru)
        self.add_edge(risk.country.Brazil, risk.country.Peru)
        self.add_edge(risk.country.Brazil, risk.country.Argentina)
        self.add_edge(risk.country.Brazil, risk.country.NorthAfrica)
        self.add_edge(risk.country.Peru, risk.country.Argentina)
        self.add_edge(risk.country.Iceland, risk.country.Greenland)
        self.add_edge(risk.country.Iceland, risk.country.GreatBritain)
        self.add_edge(risk.country.Iceland, risk.country.Scandinavia)
        self.add_edge(risk.country.GreatBritain, risk.country.Scandinavia)
        self.add_edge(risk.country.GreatBritain, risk.country.NorthernEurope)
        self.add_edge(risk.country.GreatBritain, risk.country.WesternEurope)
        self.add_edge(risk.country.Scandinavia, risk.country.NorthernEurope)
        self.add_edge(risk.country.NorthernEurope, risk.country.Ukraine)
        self.add_edge(risk.country.NorthernEurope, risk.country.SouthernEurope)
        self.add_edge(risk.country.NorthernEurope, risk.country.WesternEurope)
        self.add_edge(risk.country.Ukraine, risk.country.Scandinavia)
        self.add_edge(risk.country.Ukraine, risk.country.SouthernEurope)
        self.add_edge(risk.country.Ukraine, risk.country.Ural)
        self.add_edge(risk.country.Ukraine, risk.country.Afghanistan)
        self.add_edge(risk.country.Ukraine, risk.country.MiddleEast)
        self.add_edge(risk.country.WesternEurope, risk.country.SouthernEurope)
        self.add_edge(risk.country.SouthernEurope, risk.country.Egypt)
        self.add_edge(risk.country.SouthernEurope, risk.country.MiddleEast)
        self.add_edge(risk.country.NorthAfrica, risk.country.Brazil)
        self.add_edge(risk.country.NorthAfrica, risk.country.WesternEurope)
        self.add_edge(risk.country.NorthAfrica, risk.country.Egypt)
        self.add_edge(risk.country.NorthAfrica, risk.country.EastAfrica)
        self.add_edge(risk.country.NorthAfrica, risk.country.Congo)
        self.add_edge(risk.country.Egypt, risk.country.EastAfrica)
        self.add_edge(risk.country.Egypt, risk.country.MiddleEast)
        self.add_edge(risk.country.EastAfrica, risk.country.Congo)
        self.add_edge(risk.country.EastAfrica, risk.country.SouthAfrica)
        self.add_edge(risk.country.EastAfrica, risk.country.Madagascar)
        self.add_edge(risk.country.Congo, risk.country.SouthAfrica)
        self.add_edge(risk.country.SouthAfrica, risk.country.Madagascar)
        self.add_edge(risk.country.Ural, risk.country.Siberia)
        self.add_edge(risk.country.Ural, risk.country.China)
        self.add_edge(risk.country.Ural, risk.country.Afghanistan)
        self.add_edge(risk.country.Siberia, risk.country.Yakutsk)
        self.add_edge(risk.country.Siberia, risk.country.Irkutsk)
        self.add_edge(risk.country.Siberia, risk.country.Mongolia)
        self.add_edge(risk.country.Siberia, risk.country.China)
        self.add_edge(risk.country.Yakutsk, risk.country.Irkutsk)
        self.add_edge(risk.country.Irkutsk, risk.country.Mongolia)
        self.add_edge(risk.country.Irkutsk, risk.country.Kamchatka)
        self.add_edge(risk.country.Kamchatka, risk.country.Yakutsk)
        self.add_edge(risk.country.Kamchatka, risk.country.Japan)
        self.add_edge(risk.country.Kamchatka, risk.country.Mongolia)
        self.add_edge(risk.country.Mongolia, risk.country.China)
        self.add_edge(risk.country.Mongolia, risk.country.Japan)
        self.add_edge(risk.country.China, risk.country.Mongolia)
        self.add_edge(risk.country.China, risk.country.India)
        self.add_edge(risk.country.China, risk.country.Siam)
        self.add_edge(risk.country.India, risk.country.Siam)
        self.add_edge(risk.country.India, risk.country.MiddleEast)
        self.add_edge(risk.country.Afghanistan, risk.country.China)
        self.add_edge(risk.country.Afghanistan, risk.country.India)
        self.add_edge(risk.country.Afghanistan, risk.country.MiddleEast)
        self.add_edge(risk.country.Indonesia, risk.country.Siam)
        self.add_edge(risk.country.Indonesia, risk.country.NewGuinea)
        self.add_edge(risk.country.Indonesia, risk.country.WesternAustralia)
        self.add_edge(risk.country.NewGuinea, risk.country.EasternAustralia)
        self.add_edge(risk.country.NewGuinea, risk.country.WesternAustralia)
        self.add_edge(risk.country.EasternAustralia, risk.country.WesternAustralia)
        self.add_edge(risk.country.Alaska, risk.country.Kamchatka)
        self.add_edge(risk.country.Greenland, risk.country.Iceland)
        self.add_edge(risk.country.Brazil, risk.country.NorthAfrica)
        self.add_edge(risk.country.SouthernEurope, risk.country.Egypt)
        self.add_edge(risk.country.WesternEurope, risk.country.NorthAfrica)
        self.add_edge(risk.country.SouthernEurope, risk.country.NorthAfrica)
        self.add_edge(risk.country.EastAfrica, risk.country.MiddleEast)
        self.add_edge(risk.country.Ukraine, risk.country.Ural)
        self.add_edge(risk.country.Ukraine, risk.country.Afghanistan)
        self.add_edge(risk.country.Ukraine, risk.country.MiddleEast)
        self.add_edge(risk.country.Siam, risk.country.Indonesia)

    # cannot call .subgraph() on the main class; it causes
    # an indirect call to the constructor, which generates an additional empty plot
    def get_subgraph(self, countries: List[risk.country.Country]):
        subgraph = nx.Graph()
        subgraph.add_nodes_from(countries)
        for u, v in self.edges():
            if u in countries and v in countries:
                subgraph.add_edge(u, v)

        return subgraph
