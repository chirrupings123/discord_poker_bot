import random


SUITS = ["h", "d", "c", "s"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]

SUIT_SYMBOLS = {"h": "♥", "d": "♦", "c": "♣", "s": "♠"}
SUIT_NAMES = {"h": "Hearts", "d": "Diamonds", "c": "Clubs", "s": "Spades"}
RANK_NAMES = {
    "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7",
    "8": "8", "9": "9", "10": "10", "J": "Jack", "Q": "Queen",
    "K": "King", "A": "Ace",
}

RANK_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12,
    "K": 13, "A": 14,
}


class Card:
    __slots__ = ("rank", "suit")

    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit

    @property
    def value(self) -> int:
        return RANK_VALUES[self.rank]

    def __repr__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __str__(self) -> str:
        return f"{self.rank}{SUIT_SYMBOLS[self.suit]}"

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return hash((self.rank, self.suit))


class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            raise ValueError("No cards left in deck")
        return self.cards.pop()

    def draw_multiple(self, count: int) -> list[Card]:
        return [self.draw() for _ in range(count)]

    def __len__(self):
        return len(self.cards)

    def __repr__(self) -> str:
        return f"Deck({len(self.cards)} cards)"
