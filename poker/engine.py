"""
Poker game engine.

Manages the state of a single hand of Texas Hold'em.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from poker.deck import Card, Deck
from poker.hand_evaluator import evaluate_hand, hand_name


class Round(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


@dataclass
class PlayerState:
    user_id: int
    seat_index: int
    hole_cards: list[Card] = field(default_factory=list)
    chips: float = 0.0
    chips_at_start: float = 0.0
    current_bet: float = 0.0
    total_bet: float = 0.0
    is_active: bool = True
    has_folded: bool = False
    is_all_in: bool = False
    is_winner: bool = False
    hand_rank: Optional[str] = None
    net_won: float = 0.0

    def reset_bet(self):
        self.current_bet = 0.0

    def can_act(self) -> bool:
        return self.is_active and not self.has_folded and not self.is_all_in and self.chips > 0


@dataclass
class SidePot:
    amount: float = 0.0
    eligible: set[int] = field(default_factory=set)


class PokerEngine:
    """
    Core poker game logic for a single hand.
    Does not interact with Discord or the database directly.
    """

    def __init__(
        self,
        players: list[PlayerState],
        dealer_position: int,
        small_blind: float = 10.0,
        big_blind: float = 20.0,
    ):
        self.players = sorted(players, key=lambda p: p.seat_index)
        self.dealer_position = dealer_position
        self.small_blind_amount = small_blind
        self.big_blind_amount = big_blind
        self.deck = Deck()
        self.community_cards: list[Card] = []
        self.round = Round.PREFLOP
        self.pots: list[SidePot] = [SidePot()]
        self.current_bet = 0.0
        self.min_raise = big_blind
        self.last_raiser: Optional[int] = None
        self.hand_over = False
        self.action_history: list[dict] = []
        self._action_count = 0
        self._deal_hole_cards()
        self._post_blinds()
        self.current_bet = self.big_blind_amount
        self.min_raise = self.big_blind_amount
        self.current_player_index = self._first_to_act()
        self._players_acted_in_round: set[int] = set()

    def _deal_hole_cards(self):
        for player in self.active_players:
            player.hole_cards = self.deck.draw_multiple(2)
            player.chips_at_start = player.chips

    @property
    def active_players(self) -> list[PlayerState]:
        return [p for p in self.players if p.is_active]

    @property
    def players_in_hand(self) -> list[PlayerState]:
        return [p for p in self.active_players if not p.has_folded]

    def _post_blinds(self):
        active = self.active_players
        if len(active) < 2:
            return

        if len(active) == 2:
            sb_idx = self.dealer_position
            bb_idx = (self.dealer_position + 1) % 2
        else:
            sb_idx = (self.dealer_position + 1) % len(active)
            bb_idx = (self.dealer_position + 2) % len(active)

        sb_player = active[sb_idx]
        bb_player = active[bb_idx]

        self._post_bet(sb_player, min(self.small_blind_amount, sb_player.chips))
        self._post_bet(bb_player, min(self.big_blind_amount, bb_player.chips))

        self.last_raiser = bb_player.user_id

    def _post_bet(self, player: PlayerState, amount: float):
        actual = min(amount, player.chips)
        player.chips -= actual
        player.current_bet += actual
        player.total_bet += actual
        self.pots[0].amount += actual
        self.pots[0].eligible.add(player.user_id)
        if player.chips <= 0:
            player.is_all_in = True

    def _first_to_act(self) -> int:
        active = self.active_players
        if len(active) <= 2:
            return self.dealer_position % len(active)
        bb_idx = (self.dealer_position + 2) % len(active)
        return (bb_idx + 1) % len(active)

    def _first_to_act_postflop(self) -> int:
        active = self.active_players
        for i in range(1, len(active) + 1):
            idx = (self.dealer_position + i) % len(active)
            if active[idx].can_act():
                return idx
        return -1

    def _next_active_player(self, from_idx: int) -> int:
        active = self.active_players
        for _ in range(1, len(active) + 1):
            idx = (from_idx + 1) % len(active)
            if active[idx].can_act():
                return idx
            from_idx = idx
        return -1

    def can_act_player(self) -> Optional[PlayerState]:
        if self.hand_over or self.current_player_index < 0:
            return None
        players = self.active_players
        if self.current_player_index >= len(players):
            return None
        return players[self.current_player_index]

    def can_check(self) -> bool:
        player = self.can_act_player()
        if not player:
            return False
        return player.current_bet >= self.current_bet

    def get_call_amount(self) -> float:
        player = self.can_act_player()
        if not player:
            return 0
        remaining = self.current_bet - player.current_bet
        if remaining <= 0:
            return 0
        return min(remaining, player.chips)

    def get_min_raise(self) -> float:
        player = self.can_act_player()
        if not player:
            return 0
        total_needed = player.current_bet + self.min_raise + (self.current_bet - player.current_bet)
        return min(total_needed, player.chips + player.current_bet)

    def fold(self) -> dict:
        player = self.can_act_player()
        if not player:
            return {"error": "No player to act"}
        player.has_folded = True
        self.action_history.append({
            "player_id": player.user_id,
            "action": "fold",
            "amount": 0,
        })
        return self._advance()

    def check(self) -> dict:
        player = self.can_act_player()
        if not player:
            return {"error": "No player to act"}
        if not self.can_check():
            return {"error": "Cannot check when there is a bet"}
        self._players_acted_in_round.add(player.user_id)
        self.action_history.append({
            "player_id": player.user_id,
            "action": "check",
            "amount": 0,
        })
        return self._advance()

    def call(self) -> dict:
        player = self.can_act_player()
        if not player:
            return {"error": "No player to act"}
        call_amount = self.current_bet - player.current_bet
        if call_amount <= 0:
            return self.check()
        actual = min(call_amount, player.chips)
        self._post_bet(player, actual)
        self._players_acted_in_round.add(player.user_id)
        self.action_history.append({
            "player_id": player.user_id,
            "action": "call",
            "amount": actual,
        })
        return self._advance()

    def raise_bet(self, amount: float) -> dict:
        player = self.can_act_player()
        if not player:
            return {"error": "No player to act"}
        total_needed = amount
        min_allowed = self.current_bet + self.min_raise
        if total_needed < min_allowed and total_needed < player.chips + player.current_bet:
            return {"error": f"Minimum total bet is {min_allowed}"}
        if total_needed > player.chips + player.current_bet:
            total_needed = player.chips + player.current_bet
        bet_added = total_needed - player.current_bet
        self._post_bet(player, bet_added)
        self.current_bet = total_needed
        self.min_raise = max(self.min_raise, bet_added)
        self.last_raiser = player.user_id
        self._players_acted_in_round = {player.user_id}
        self.action_history.append({
            "player_id": player.user_id,
            "action": "raise",
            "amount": total_needed,
        })
        return self._advance()

    def all_in(self) -> dict:
        player = self.can_act_player()
        if not player:
            return {"error": "No player to act"}
        total_now = player.current_bet + player.chips
        self._post_bet(player, player.chips)
        player.is_all_in = True
        if total_now > self.current_bet:
            self.current_bet = total_now
            self.last_raiser = player.user_id
            self._players_acted_in_round = {player.user_id}
        else:
            self._players_acted_in_round.add(player.user_id)
        self.action_history.append({
            "player_id": player.user_id,
            "action": "all_in",
            "amount": total_now,
        })
        return self._advance()

    def _advance(self) -> dict:
        result = {"success": True}

        if self._is_hand_over():
            if len(self.players_in_hand) == 1:
                self._award_to_last_standing(self.players_in_hand[0])
            else:
                self._handle_showdown()
            self.hand_over = True
            return result

        if self._is_round_over():
            self._next_round()
            return result

        next_idx = self._next_active_player(self.current_player_index)
        if next_idx != -1:
            self.current_player_index = next_idx
        else:
            if self._is_round_over():
                self._next_round()

        return result

    def _is_hand_over(self) -> bool:
        if len(self.players_in_hand) <= 1:
            return True
        can_act = [p for p in self.players_in_hand if p.can_act()]
        if not can_act:
            return True
        return False

    def _is_round_over(self) -> bool:
        active = self.players_in_hand
        if len(active) <= 1:
            return True

        can_act = [p for p in active if p.can_act()]
        if not can_act:
            return True

        all_equal = all(
            p.current_bet == self.current_bet or not p.can_act()
            for p in active
        )
        if not all_equal:
            return False

        if self.last_raiser is None:
            return len(self._players_acted_in_round) >= len(can_act)

        raiser_acted = self.last_raiser in self._players_acted_in_round
        everyone_else_acted = all(
            p.user_id in self._players_acted_in_round or not p.can_act() or p.user_id == self.last_raiser
            for p in active
        )
        if raiser_acted and everyone_else_acted:
            return True

        return False

    def _next_round(self):
        for p in self.active_players:
            p.reset_bet()
        self.current_bet = 0
        self.min_raise = self.big_blind_amount
        self.last_raiser = None
        self._players_acted_in_round = set()

        if self.round == Round.PREFLOP:
            self.round = Round.FLOP
            self.community_cards.extend(self.deck.draw_multiple(3))
        elif self.round == Round.FLOP:
            self.round = Round.TURN
            self.community_cards.extend(self.deck.draw_multiple(1))
        elif self.round == Round.TURN:
            self.round = Round.RIVER
            self.community_cards.extend(self.deck.draw_multiple(1))
        elif self.round == Round.RIVER:
            self.round = Round.SHOWDOWN
            self._handle_showdown()
            self.hand_over = True
            return

        self.current_player_index = self._first_to_act_postflop()

    def _award_to_last_standing(self, player: PlayerState):
        total_pot = sum(p.amount for p in self.pots)
        player.net_won = total_pot - player.total_bet
        player.chips += (total_pot - player.total_bet)
        self.pots = [SidePot(amount=0)]
        self.round = Round.SHOWDOWN
        self.hand_over = True

    def _compute_side_pots(self):
        active = self.players_in_hand
        if not active:
            self.pots = [SidePot()]
            return

        sorted_players = sorted(active, key=lambda p: p.total_bet)
        pots = []
        prev_bet = 0.0
        remaining_total = sum(p.total_bet for p in active)

        for player in sorted_players:
            if player.total_bet > prev_bet:
                diff = player.total_bet - prev_bet
                contributors = [p for p in active if p.total_bet >= player.total_bet]
                side_amount = diff * len(contributors)
                if side_amount > 0:
                    side_pot = SidePot(
                        amount=side_amount,
                        eligible={p.user_id for p in contributors},
                    )
                    pots.append(side_pot)
                prev_bet = player.total_bet

        main_pot_total = sum(p.amount for p in pots)
        leftover = remaining_total - main_pot_total
        if leftover > 0.01:
            if pots:
                pots[0].amount += leftover
            else:
                pots.append(SidePot(amount=leftover, eligible={p.user_id for p in active}))

        self.pots = pots if pots else [SidePot()]

    def _handle_showdown(self):
        self._compute_side_pots()
        active = self.players_in_hand
        self.hand_over = True

        if not active:
            return

        for i, pot in enumerate(self.pots):
            eligible = [p for p in active if p.user_id in pot.eligible]
            if not eligible:
                continue

            best_score = None
            winners = []
            for player in eligible:
                if not player.hole_cards:
                    continue
                all_cards = player.hole_cards + self.community_cards
                score = evaluate_hand(all_cards)
                if best_score is None or score > best_score:
                    best_score = score
                    winners = [player]
                elif score == best_score:
                    winners.append(player)

            if not winners:
                continue

            share = pot.amount / len(winners)
            for winner in winners:
                winner.is_winner = True
                winner.net_won += share - winner.total_bet
                winner.chips += share
                winner.hand_rank = hand_name(best_score.rank)

    def public_state(self) -> dict:
        return {
            "round": self.round.value,
            "community_cards": [str(c) for c in self.community_cards],
            "pots": [{"amount": p.amount, "eligible": list(p.eligible)} for p in self.pots],
            "total_pot": sum(p.amount for p in self.pots),
            "current_bet": self.current_bet,
            "dealer_position": self.dealer_position,
            "current_player": self.can_act_player().user_id if self.can_act_player() else None,
            "players": [
                {
                    "user_id": p.user_id,
                    "chips": p.chips,
                    "current_bet": p.current_bet,
                    "total_bet": p.total_bet,
                    "is_active": p.is_active,
                    "has_folded": p.has_folded,
                    "is_all_in": p.is_all_in,
                    "hand_rank": p.hand_rank,
                    "net_won": p.net_won,
                }
                for p in self.active_players + [p for p in self.players if not p.is_active]
            ],
        }
