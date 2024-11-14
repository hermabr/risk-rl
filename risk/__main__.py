import random
import networkx as nx
from risk.game import Game
from risk.country import *
from risk.player import Player
from risk.soldier import Soldier

game = Game([Player('Player 1'), Player('Player 2'), Player('Player 3')])

game.visualize()

