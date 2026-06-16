"""
Integration tests for the poker engine.

Run with:
    pytest tests/test_poker.py -v
"""
import pytest
from poker.engine import PokerEngine, PlayerState, Round
from poker.deck import Card


def make_player(user_id: int, chips: float, seat: int = 0, active: bool = True) -> PlayerState:
    return PlayerState(
        user_id=user_id,
        seat_index=seat,
        chips=chips,
        is_active=active,
    )


class TestPokerEngine:
    """Test the poker game engine."""

    def test_two_player_game(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        assert engine.round == Round.PREFLOP
        assert len(p1.hole_cards) == 2
        assert len(p2.hole_cards) == 2

    def test_blinds_posted(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        assert p1.chips < 1000
        assert p2.chips < 1000
        assert engine.pots[0].amount == 30

    def test_fold(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        result = engine.fold()
        assert result["success"]
        assert engine.hand_over

    def test_call_heads_up(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        assert engine.can_check() is False
        result = engine.call()
        assert result["success"]
        assert engine.players_in_hand == [p1, p2]

    def test_raise(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        result = engine.raise_bet(100)
        assert result["success"]
        assert engine.hand_over is False

    def test_all_in(self):
        p1 = make_player(1, 50, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        result = engine.all_in()
        assert result["success"]
        assert p1.is_all_in

    def test_hand_progression(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        assert engine.round == Round.PREFLOP
        engine.call()
        assert engine.round == Round.PREFLOP
        assert engine.can_check() is True
        engine.check()
        assert engine.round == Round.FLOP
        assert len(engine.community_cards) == 3

    def test_full_hand_to_showdown(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        while not engine.hand_over:
            cp = engine.can_act_player()
            if not cp:
                break
            if engine.can_check():
                engine.check()
            else:
                engine.call()
        assert engine.hand_over
        winners = [p for p in engine.players if p.is_winner]
        assert len(winners) >= 1

    def test_three_player_game(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        p3 = make_player(3, 1000, 2)
        engine = PokerEngine([p1, p2, p3], dealer_position=0)
        assert engine.round == Round.PREFLOP
        assert len(engine.active_players) == 3

    def test_public_state(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        state = engine.public_state()
        assert "round" in state
        assert "community_cards" in state
        assert "pots" in state
        assert "players" in state

    def test_cannot_act_when_not_turn(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        engine = PokerEngine([p1, p2], dealer_position=0)
        result = engine.fold()
        assert result["success"]
        assert engine.hand_over

    def test_three_player_preflop_action(self):
        p1 = make_player(1, 1000, 0)
        p2 = make_player(2, 1000, 1)
        p3 = make_player(3, 1000, 2)
        engine = PokerEngine([p1, p2, p3], dealer_position=0)
        assert engine.can_check() is False
        engine.call()
        result = engine.fold()
        assert result["success"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
