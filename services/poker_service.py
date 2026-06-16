"""
Service layer for poker table management in the database.
"""
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import GameTable, TableStatus, Game, GameStatus, GamePlayer, GameHistory
from poker.game_manager import ActiveTable


async def create_table_db(
    session: AsyncSession,
    channel_id: int,
    guild_id: int,
    host_id: int,
    buy_in: float,
    max_players: int = 9,
) -> GameTable:
    table = GameTable(
        channel_id=channel_id,
        guild_id=guild_id,
        host_id=host_id,
        status=TableStatus.WAITING,
        buy_in=buy_in,
        max_players=max_players,
    )
    session.add(table)
    await session.commit()
    await session.refresh(table)
    return table


async def get_table_db(session: AsyncSession, table_id: int) -> GameTable | None:
    return await session.get(GameTable, table_id)


async def set_table_status(session: AsyncSession, table_id: int, status: TableStatus):
    table = await session.get(GameTable, table_id)
    if table:
        table.status = status
        await session.commit()


async def create_game_record(
    session: AsyncSession,
    table_id: int,
    hand_number: int,
    dealer_position: int,
    small_blind: float,
    big_blind: float,
) -> Game:
    game = Game(
        table_id=table_id,
        status=GameStatus.PREFLOP,
        hand_number=hand_number,
        dealer_position=dealer_position,
    )
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return game


async def save_game_player(
    session: AsyncSession,
    game_id: int,
    user_id: int,
    position: int,
    chips_at_start: float,
    hole_cards: str = None,
):
    gp = GamePlayer(
        game_id=game_id,
        user_id=user_id,
        position=position,
        hole_cards=hole_cards,
        chips_at_start=chips_at_start,
    )
    session.add(gp)
    await session.commit()
    return gp


async def log_action(
    session: AsyncSession,
    game_id: int,
    round_name: str,
    action: str,
    player_id: int | None = None,
    amount: float | None = None,
):
    entry = GameHistory(
        game_id=game_id,
        round_name=round_name,
        action=action,
        player_id=player_id,
        amount=amount,
    )
    session.add(entry)
    await session.commit()
