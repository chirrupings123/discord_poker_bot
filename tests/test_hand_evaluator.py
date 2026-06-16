"""
Automated tests for the hand evaluator.

Run with:
    pytest tests/test_hand_evaluator.py -v
"""
import pytest
from poker.deck import Card
from poker.hand_evaluator import evaluate_hand, HandScore


def c(rank: str, suit: str = "s") -> Card:
    return Card(rank, suit)


class TestHandEvaluation:
    """Verify all hand rankings are evaluated correctly."""

    def test_high_card(self):
        cards = [c("2", "h"), c("4", "d"), c("7", "c"), c("9", "s"), c("J", "h")]
        score = evaluate_hand(cards)
        assert score.rank == 0

    def test_pair(self):
        cards = [c("2"), c("2", "h"), c("7"), c("9"), c("J")]
        score = evaluate_hand(cards)
        assert score.rank == 1

    def test_two_pair(self):
        cards = [c("2"), c("2", "h"), c("7"), c("7", "h"), c("J")]
        score = evaluate_hand(cards)
        assert score.rank == 2

    def test_three_of_a_kind(self):
        cards = [c("2"), c("2", "h"), c("2", "d"), c("9"), c("J")]
        score = evaluate_hand(cards)
        assert score.rank == 3

    def test_straight(self):
        cards = [c("5", "h"), c("6", "d"), c("7", "c"), c("8", "s"), c("9", "h")]
        score = evaluate_hand(cards)
        assert score.rank == 4

    def test_straight_low_ace(self):
        cards = [c("A", "h"), c("2", "d"), c("3", "c"), c("4", "s"), c("5", "h")]
        score = evaluate_hand(cards)
        assert score.rank == 4

    def test_flush(self):
        cards = [c("2", "h"), c("5", "h"), c("7", "h"), c("9", "h"), c("J", "h")]
        score = evaluate_hand(cards)
        assert score.rank == 5

    def test_full_house(self):
        cards = [c("2"), c("2", "h"), c("2", "d"), c("7"), c("7", "h")]
        score = evaluate_hand(cards)
        assert score.rank == 6

    def test_four_of_a_kind(self):
        cards = [c("2"), c("2", "h"), c("2", "d"), c("2", "c"), c("7")]
        score = evaluate_hand(cards)
        assert score.rank == 7

    def test_straight_flush(self):
        cards = [c("5", "s"), c("6", "s"), c("7", "s"), c("8", "s"), c("9", "s")]
        score = evaluate_hand(cards)
        assert score.rank == 8

    def test_royal_flush(self):
        cards = [c("10", "s"), c("J", "s"), c("Q", "s"), c("K", "s"), c("A", "s")]
        score = evaluate_hand(cards)
        assert score.rank == 9

    def test_straight_flush_beats_four_of_a_kind(self):
        sf = evaluate_hand([c("5", "s"), c("6", "s"), c("7", "s"), c("8", "s"), c("9", "s")])
        fk = evaluate_hand([c("2"), c("2", "h"), c("2", "d"), c("2", "c"), c("7")])
        assert sf > fk

    def test_flush_beats_straight(self):
        flush = evaluate_hand([c("2", "h"), c("5", "h"), c("7", "h"), c("9", "h"), c("J", "h")])
        straight = evaluate_hand([c("5", "d"), c("6", "c"), c("7", "s"), c("8", "h"), c("9", "d")])
        assert flush > straight

    def test_pair_kickers(self):
        pair_a = evaluate_hand([c("A"), c("A", "h"), c("2"), c("3"), c("4")])
        pair_k = evaluate_hand([c("K"), c("K", "h"), c("2"), c("3"), c("4")])
        assert pair_a > pair_k

    def test_best_from_seven(self):
        """With 7 cards, should pick the best 5-card hand."""
        cards = [
            c("A"), c("K"),
            c("A", "h"), c("A", "d"), c("A", "c"),
            c("2"), c("3"),
        ]
        score = evaluate_hand(cards)
        assert score.rank == 7

    def test_best_from_seven_full_house(self):
        cards = [
            c("A"), c("K"),
            c("A", "h"), c("A", "d"), c("K", "h"),
            c("2"), c("3"),
        ]
        score = evaluate_hand(cards)
        assert score.rank == 6

    def test_hand_score_comparison(self):
        s1 = evaluate_hand([c("5", "d"), c("6", "c"), c("7", "s"), c("8", "h"), c("9", "d")])
        s2 = evaluate_hand([c("5", "s"), c("6", "s"), c("7", "s"), c("8", "s"), c("9", "s")])
        assert s1.rank == 4
        assert s2.rank == 8
        assert s2 > s1

    def test_split_pot_scenario(self):
        h1 = [c("A", "d"), c("K", "d"), c("Q", "d"), c("J", "d"), c("10", "d")]
        h2 = [c("A", "s"), c("K", "s"), c("Q", "s"), c("J", "s"), c("10", "s")]
        s1 = evaluate_hand(h1)
        s2 = evaluate_hand(h2)
        assert s1 == s2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
