"""
Texas Hold'em hand evaluator.

Evaluates the best 5-card hand from 7 available cards (2 hole + 5 community).
Returns a numeric score for comparison and a human-readable hand name.

Hand rankings (high card = 0 ... royal flush = 9):
  HIGH_CARD = 0
  PAIR = 1
  TWO_PAIR = 2
  THREE_OF_A_KIND = 3
  STRAIGHT = 4
  FLUSH = 5
  FULL_HOUSE = 6
  FOUR_OF_A_KIND = 7
  STRAIGHT_FLUSH = 8
  ROYAL_FLUSH = 9
"""

from collections import Counter
from itertools import combinations
from typing import NamedTuple

from poker.deck import Card, RANK_VALUES, SUITS

HAND_RANK_NAMES = {
    9: "Royal Flush",
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "Pair",
    0: "High Card",
}


class HandScore(NamedTuple):
    rank: int
    values: tuple[int, ...]

    def __lt__(self, other):
        if self.rank != other.rank:
            return self.rank < other.rank
        return self.values < other.values

    def __gt__(self, other):
        if self.rank != other.rank:
            return self.rank > other.rank
        return self.values > other.values

    def __eq__(self, other):
        return self.rank == other.rank and self.values == other.values

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    def __ne__(self, other):
        return not self.__eq__(other)


def _royal_flush_value(values: tuple[int, ...]) -> HandScore | None:
    if values == (14, 13, 12, 11, 10):
        return HandScore(9, (14,))
    return None


def _straight_flush_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(8, values)


def _four_of_a_kind_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(7, values)


def _full_house_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(6, values)


def _flush_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(5, values)


def _straight_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(4, values)


def _three_of_a_kind_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(3, values)


def _two_pair_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(2, values)


def _pair_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(1, values)


def _high_card_value(values: tuple[int, ...]) -> HandScore:
    return HandScore(0, values)


def _get_ranks(cards: list[Card]) -> list[int]:
    return sorted([c.value for c in cards], reverse=True)


def _is_straight(values: list[int]) -> tuple[bool, list[int]]:
    unique = sorted(set(values), reverse=True)
    if len(unique) < 5:
        return False, unique

    for i in range(len(unique) - 4):
        if unique[i] - unique[i + 4] == 4:
            return True, unique[i : i + 5]

    if 14 in unique and 2 in unique and 3 in unique and 4 in unique and 5 in unique:
        return True, [5, 4, 3, 2, 1]

    return False, unique


def _is_flush(cards: list[Card]) -> bool:
    suit_counts = Counter(c.suit for c in cards)
    return any(count >= 5 for count in suit_counts.values())


def _get_flush_cards(cards: list[Card]) -> list[Card]:
    suit_counts = Counter(c.suit for c in cards)
    for suit, count in suit_counts.items():
        if count >= 5:
            flush_cards = [c for c in cards if c.suit == suit]
            return sorted(flush_cards, key=lambda c: c.value, reverse=True)[:5]
    return []


def evaluate_hand(cards: list[Card]) -> HandScore:
    """
    Evaluate the best 5-card hand from the given cards.

    Returns a HandScore with rank and kicker values for comparison.
    Higher rank = better hand. Same rank = kickers compared.
    """
    if len(cards) == 5:
        return _evaluate_five(cards)

    best = None
    for combo in combinations(cards, 5):
        score = _evaluate_five(list(combo))
        if best is None or score > best:
            best = score
    return best


def _evaluate_five(cards: list[Card]) -> HandScore:
    ranks = _get_ranks(cards)
    is_flush = _is_flush(cards)
    is_straight, straight_ranks = _is_straight(ranks)

    if is_flush and is_straight:
        if straight_ranks[0] == 14:
            result = _royal_flush_value(tuple(straight_ranks))
            if result:
                return result
        return _straight_flush_value(tuple(straight_ranks))

    rank_counts = Counter(c.value for c in cards)
    counts = sorted(rank_counts.items(), key=lambda x: (-x[1], -x[0]))

    if counts[0][1] == 4:
        quad = counts[0][0]
        kicker = counts[1][0]
        return _four_of_a_kind_value((quad, kicker))

    if counts[0][1] == 3 and len(counts) > 1 and counts[1][1] >= 2:
        trips = counts[0][0]
        pair = counts[1][0]
        return _full_house_value((trips, pair))

    if is_flush:
        return _flush_value(tuple(ranks[:5]))

    if is_straight:
        return _straight_value(tuple(straight_ranks))

    if counts[0][1] == 3:
        trips = counts[0][0]
        kickers = tuple(v for v, c in counts[1:])
        return _three_of_a_kind_value((trips,) + kickers)

    if counts[0][1] == 2 and len(counts) > 1 and counts[1][1] == 2:
        pairs = sorted([counts[0][0], counts[1][0]], reverse=True)
        kicker = counts[2][0] if len(counts) > 2 else 0
        return _two_pair_value((pairs[0], pairs[1], kicker))

    if counts[0][1] == 2:
        pair = counts[0][0]
        kickers = tuple(v for v, c in counts[1:])
        return _pair_value((pair,) + kickers)

    return _high_card_value(tuple(ranks[:5]))


def hand_name(hand_rank: int) -> str:
    return HAND_RANK_NAMES.get(hand_rank, "Unknown")


def best_hand_description(hole_cards: list[Card], community_cards: list[Card]) -> tuple[HandScore, str]:
    all_cards = hole_cards + community_cards
    score = evaluate_hand(all_cards)
    name = hand_name(score.rank)
    return score, name
