from enum import Enum
import random


class CardType(Enum):
    INFANTRY = "infantry"
    CAVALRY = "cavalry"
    ARTILLERY = "artillery"
    #WILDCARD = 4

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

class Card:
    def __init__(self, card_type: CardType):
        self.card_type = card_type
    
    def __eq__(self, other):
        return isinstance(other, Card) and self.card_type == other.card_type

    def __hash__(self):
        return hash(self.card_type)

def init_deck():
    deck = [Card(CardType.INFANTRY)]*14 + \
        [Card(CardType.CAVALRY)]*14 + \
        [Card(CardType.ARTILLERY)]*14 
        #[Card(CardType.WILDCARD)]*2

    random.shuffle(deck)
    return deck

trade_in_map = [4, 6, 8, 10, 12, 15]
def trade_in_rewards(n_card_trade_ins: int):
    if n_card_trade_ins <= 6:
        return trade_in_map[n_card_trade_ins - 1]

    return 15 + 5 *(n_card_trade_ins - 6)

 
