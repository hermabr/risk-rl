from abc import abstractmethod
from risk.card import *
from risk.country import Country
import risk.game

class Player:
    game: 'risk.game.Game'
    def __init__(self, name):
        self.name = name
        self.countries = []
        self.unassigned_soldiers = 0
        self.cards = {card_type: [] for card_type in CardType}
        self.n_card_trade_ins = 0

    def add_country(self, country: Country):
        self.countries.append(country)

    def remove_country(self, country: Country):
        self.countries.remove(country)
    
    def get_cards(self):
        return {k: len(v) for k,v in self.cards.items()}

    def get_trade_in_options(self):
        options = []

        if sum([min(1, len(v)) for v in self.cards.values()]) >= 3:
            # can trade in one of each
            options.append([Card(card_type) for card_type in CardType])
        
        for k, v in self.cards.items():
            if len(v) >= 3:
                # can trade in three of a kind
                options.append([Card(k)]*3)
        
        return options
            
    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    @abstractmethod
    def process_cards_phase(self):
        pass

    @abstractmethod
    def process_draft_phase(self):
        pass

    @abstractmethod
    def process_attack_phase(self):
        pass

    @abstractmethod
    def process_fortify_phase(self):
        pass
