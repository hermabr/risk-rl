import networkx as nx

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
plt.ion()

from risk.country import *

class GameMap(nx.Graph):
    def __init__(self):
        super().__init__()
        self.initialize_game_map()
        self.positions = {
            Alaska:(-2,6),NorthwestTerritory:(-1,6),Greenland:(1,6),Alberta:(-1.5,5),
            Ontario:(-0.5,5),Quebec:(0.5,5),WesternUS:(-1.5,4),EasternUS:(0,4),
            CentralAmerica:(-1,3),Venezuela:(-1,2),Brazil:(0,1),Peru:(-1,1),
            Argentina:(-1,0),Iceland:(1.5,5),GreatBritain:(2,4.5),Scandinavia:(3,5),
            NorthernEurope:(3,4),WesternEurope:(2,3.5),SouthernEurope:(3,3),
            Ukraine:(4,4.5),NorthAfrica:(1.5,2),Egypt:(3,2),EastAfrica:(3,1),
            Congo:(3,0),SouthAfrica:(3,-1),Madagascar:(4,-1),Ural:(5,5),
            Siberia:(6,5.5),Yakutsk:(7,6),Irkutsk:(7,5),Kamchatka:(8,5.5),
            Japan:(8,4),Mongolia:(7,4),China:(6,4),Afghanistan:(5,4),
            MiddleEast:(4,3),India:(5.5,3),Siam:(6.5,3),Indonesia:(7,2),
            NewGuinea:(8,1.5),WesternAustralia:(7,1),EasternAustralia:(8,0.5)
        }
        self.fig, self.ax = plt.subplots(figsize=(15, 8))
        plt.ion()  # dynamic updates of plot

    def draw_map(self):
        self.ax.clear()
        color_map = []
        players = []
        for node in self.nodes():
            if node.army and node.army.owner:
                if node.army.owner not in players:
                    players.append(node.army.owner)
                color_map.append(players.index(node.army.owner))
            else:
                color_map.append('gray')
        nx.draw(self, with_labels=True, node_color=color_map, cmap=plt.cm.tab20,
                pos=self.positions, node_size=3000, ax=self.ax)
        
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def initialize_game_map(self):
        self.add_edge(Alaska,             NorthwestTerritory)
        self.add_edge(Alaska,             Alberta)
        self.add_edge(NorthwestTerritory, Alberta)
        self.add_edge(NorthwestTerritory, Ontario)
        self.add_edge(NorthwestTerritory, Greenland)
        self.add_edge(Alberta,            Ontario)
        self.add_edge(Alberta,            WesternUS)
        self.add_edge(Ontario,            Quebec)
        self.add_edge(Ontario,            EasternUS)
        self.add_edge(Ontario,            WesternUS)
        self.add_edge(Quebec,             EasternUS)
        self.add_edge(Quebec,             Greenland)
        self.add_edge(WesternUS,          EasternUS)
        self.add_edge(WesternUS,          CentralAmerica)
        self.add_edge(EasternUS,          CentralAmerica)
        self.add_edge(Venezuela,          CentralAmerica)
        self.add_edge(Venezuela,          Brazil)
        self.add_edge(Venezuela,          Peru)
        self.add_edge(Brazil,             Peru)
        self.add_edge(Brazil,             Argentina)
        self.add_edge(Brazil,             NorthAfrica)
        self.add_edge(Peru,               Argentina)
        self.add_edge(Iceland,            Greenland)
        self.add_edge(Iceland,            GreatBritain)
        self.add_edge(Iceland,            Scandinavia)
        self.add_edge(GreatBritain,       Scandinavia)
        self.add_edge(GreatBritain,       NorthernEurope)
        self.add_edge(GreatBritain,       WesternEurope)
        self.add_edge(Scandinavia,        NorthernEurope)
        self.add_edge(NorthernEurope,     Ukraine)
        self.add_edge(NorthernEurope,     SouthernEurope)
        self.add_edge(NorthernEurope,     WesternEurope)
        self.add_edge(Ukraine,            Scandinavia)
        self.add_edge(Ukraine,            SouthernEurope)
        self.add_edge(Ukraine,            Ural)
        self.add_edge(Ukraine,            Afghanistan)
        self.add_edge(Ukraine,            MiddleEast)
        self.add_edge(WesternEurope,      SouthernEurope)
        self.add_edge(SouthernEurope,     Egypt)
        self.add_edge(SouthernEurope,     MiddleEast)
        self.add_edge(NorthAfrica,        Brazil)
        self.add_edge(NorthAfrica,        WesternEurope)
        self.add_edge(NorthAfrica,        Egypt)
        self.add_edge(NorthAfrica,        EastAfrica)
        self.add_edge(NorthAfrica,        Congo)
        self.add_edge(Egypt,              EastAfrica)
        self.add_edge(Egypt,              MiddleEast)
        self.add_edge(EastAfrica,         Congo)
        self.add_edge(EastAfrica,         SouthAfrica)
        self.add_edge(EastAfrica,         Madagascar)
        self.add_edge(Congo,              SouthAfrica)
        self.add_edge(SouthAfrica,        Madagascar)
        self.add_edge(Ural,               Siberia)
        self.add_edge(Ural,               China)
        self.add_edge(Ural,               Afghanistan)
        self.add_edge(Siberia,            Yakutsk)
        self.add_edge(Siberia,            Irkutsk)
        self.add_edge(Siberia,            Mongolia)
        self.add_edge(Siberia,            China)
        self.add_edge(Yakutsk,            Irkutsk)
        self.add_edge(Irkutsk,            Mongolia)
        self.add_edge(Irkutsk,            Kamchatka)
        self.add_edge(Kamchatka,          Yakutsk)
        self.add_edge(Kamchatka,          Japan)
        self.add_edge(Kamchatka,          Mongolia)
        self.add_edge(Mongolia,           China)
        self.add_edge(Mongolia,           Japan)
        self.add_edge(China,              Mongolia)
        self.add_edge(China,              India)
        self.add_edge(China,              Siam)
        self.add_edge(India,              Siam)
        self.add_edge(India,              MiddleEast)
        self.add_edge(Afghanistan,        China)
        self.add_edge(Afghanistan,        India)
        self.add_edge(Afghanistan,        MiddleEast)
        self.add_edge(Indonesia,          Siam)
        self.add_edge(Indonesia,          NewGuinea)
        self.add_edge(Indonesia,          WesternAustralia)
        self.add_edge(NewGuinea,          EasternAustralia)
        self.add_edge(NewGuinea,          WesternAustralia)
        self.add_edge(EasternAustralia,   WesternAustralia)
        self.add_edge(Alaska,             Kamchatka)
        self.add_edge(Greenland,          Iceland)
        self.add_edge(Brazil,             NorthAfrica)
        self.add_edge(SouthernEurope,     Egypt)
        self.add_edge(WesternEurope,      NorthAfrica)
        self.add_edge(SouthernEurope,     NorthAfrica)
        self.add_edge(EastAfrica,         MiddleEast)
        self.add_edge(Ukraine,            Ural)
        self.add_edge(Ukraine,            Afghanistan)
        self.add_edge(Ukraine,            MiddleEast)
        self.add_edge(Siam,               Indonesia)
