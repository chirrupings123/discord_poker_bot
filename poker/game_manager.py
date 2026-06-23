"""
High-level manager for poker table sessions.

Tracks active tables in memory, manages hand progression,
and coordinates between the engine and the Discord views/services.
"""
from __future__ import annotations

import asyncio
import random
from enum import Enum
from typing import Optional, Callable, Awaitable

from poker.engine import PokerEngine, PlayerState, Round as EngineRound
from poker.hand_evaluator import evaluate_hand, hand_name


class TableState(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    HAND_COMPLETE = "hand_complete"


class ActiveTable:
    def __init__(
        self,
        table_id: int,
        channel_id: int,
        guild_id: int,
        host_id: int,
        buy_in: float,
        max_players: int = 9,
    ):
        self.table_id = table_id
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.host_id = host_id
        self.buy_in = buy_in
        self.max_players = max_players
        self.state = TableState.WAITING
        self.seated_players: dict[int, PlayerState] = {}
        self.engine: Optional[PokerEngine] = None
        self.dealer_position = 0
        self.hand_number = 0
        self.small_blind = 10
        self.big_blind = 20
        self.action_lock = asyncio.Lock()
        self.turn_timeout = 60
        self._turn_task: Optional[asyncio.Task] = None

    @property
    def player_count(self) -> int:
        return len(self.seated_players)

    @property
    def player_user_ids(self) -> list[int]:
        return list(self.seated_players.keys())

    def add_player(self, user_id: int, chips: float) -> bool:
        if user_id in self.seated_players:
            return False
        if len(self.seated_players) >= self.max_players:
            return False
        seat = len(self.seated_players)
        self.seated_players[user_id] = PlayerState(
            user_id=user_id,
            seat_index=seat,
            chips=chips,
        )
        return True

    def remove_player(self, user_id: int) -> bool:
        if user_id not in self.seated_players:
            return False
        del self.seated_players[user_id]
        return True

    def can_start(self) -> bool:
        return (
            self.state == TableState.WAITING
            and len(self.seated_players) >= 2
        )

    def get_player_view(self, user_id: int) -> Optional[dict]:
        if user_id not in self.seated_players:
            return None
        player = self.seated_players[user_id]
        if self.engine is None:
            return None
        pub = self.engine.public_state()
        pub["your_hole_cards"] = [str(c) for c in player.hole_cards]
        pub["your_chips"] = player.chips
        pub["your_bet"] = player.current_bet
        pub["your_total_bet"] = player.total_bet
        pub["table_id"] = self.table_id
        pub["hand_number"] = self.hand_number
        return pub

    def start_new_hand(self):
        self.hand_number += 1
        players = [
            p for p in self.seated_players.values()
            if p.is_active and p.chips > 0
        ]
        if len(players) < 2:
            return None

        players.sort(key=lambda p: p.seat_index)
        for i, p in enumerate(players):
            p.seat_index = i
            p.hole_cards = []
            p.current_bet = 0.0
            p.total_bet = 0.0
            p.has_folded = False
            p.is_all_in = False
            p.is_winner = False
            p.hand_rank = None
            p.net_won = 0.0

        for p in self.seated_players.values():
            if p not in players:
                p.is_active = False

        self.engine = PokerEngine(
            players=players,
            dealer_position=self.dealer_position,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
        )
        self.dealer_position = (self.dealer_position + 1) % len(players)
        self.state = TableState.PLAYING
        return self.engine


active_tables: dict[int, ActiveTable] = {}
_table_id_counter = 0


def create_table(
    table_id: int,
    channel_id: int,
    guild_id: int,
    host_id: int,
    buy_in: float,
    max_players: int = 9,
) -> ActiveTable:
    table = ActiveTable(
        table_id=table_id,
        channel_id=channel_id,
        guild_id=guild_id,
        host_id=host_id,
        buy_in=buy_in,
        max_players=max_players,
    )
    active_tables[table_id] = table
    return table


def get_table(table_id: int) -> Optional[ActiveTable]:
    return active_tables.get(table_id)


def remove_table(table_id: int):
    active_tables.pop(table_id, None)


def list_tables() -> list[ActiveTable]:
    return list(active_tables.values())
