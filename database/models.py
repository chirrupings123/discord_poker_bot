import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, BigInteger, String, Numeric, DateTime, Enum,
    ForeignKey, Text, Boolean, Index, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=False)
    username = Column(String(255), nullable=False)
    balance = Column(Numeric(18, 2), nullable=False, default=10000.00)
    registered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_rebuy_at = Column(DateTime(timezone=True), nullable=True)
    rebuy_count = Column(Integer, nullable=False, default=0)
    total_hands_played = Column(Integer, nullable=False, default=0)
    total_hands_won = Column(Integer, nullable=False, default=0)
    biggest_pot_won = Column(Numeric(18, 2), nullable=False, default=0.00)
    lifetime_winnings = Column(Numeric(18, 2), nullable=False, default=0.00)
    lifetime_losses = Column(Numeric(18, 2), nullable=False, default=0.00)
    is_banned = Column(Boolean, nullable=False, default=False)

    transactions = relationship("Transaction", back_populates="user", lazy="selectin")
    player_statistics = relationship("PlayerStatistics", back_populates="user", lazy="selectin")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', balance={self.balance})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    reason = Column(String(255), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    game_id = Column(BigInteger, ForeignKey("games.id", ondelete="SET NULL"), nullable=True)

    user = relationship("User", back_populates="transactions")

    __table_args__ = (
        Index("idx_transactions_user_id", "user_id"),
        Index("idx_transactions_timestamp", "timestamp"),
    )


class TableStatus(str, enum.Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class GameTable(Base):
    __tablename__ = "tables"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    host_id = Column(BigInteger, nullable=False)
    status = Column(Enum(TableStatus), nullable=False, default=TableStatus.WAITING)
    buy_in = Column(Numeric(18, 2), nullable=False)
    max_players = Column(Integer, nullable=False, default=9)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    games = relationship("Game", back_populates="table", lazy="selectin")

    __table_args__ = (
        Index("idx_tables_status", "status"),
    )


class GameStatus(str, enum.Enum):
    WAITING = "waiting"
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    FINISHED = "finished"


class Game(Base):
    __tablename__ = "games"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_id = Column(BigInteger, ForeignKey("tables.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(GameStatus), nullable=False, default=GameStatus.WAITING)
    hand_number = Column(Integer, nullable=False, default=0)
    dealer_position = Column(Integer, nullable=False, default=0)
    current_player_index = Column(Integer, nullable=False, default=0)
    community_cards = Column(Text, nullable=True)
    pot = Column(Numeric(18, 2), nullable=False, default=0.00)
    current_bet = Column(Numeric(18, 2), nullable=False, default=0.00)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    winner_id = Column(BigInteger, nullable=True)

    table = relationship("GameTable", back_populates="games")
    players = relationship("GamePlayer", back_populates="game", lazy="selectin")
    history = relationship("GameHistory", back_populates="game", lazy="selectin")


class GamePlayer(Base):
    __tablename__ = "game_players"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    game_id = Column(BigInteger, ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    position = Column(Integer, nullable=False)
    hole_cards = Column(Text, nullable=True)
    current_bet = Column(Numeric(18, 2), nullable=False, default=0.00)
    total_bet = Column(Numeric(18, 2), nullable=False, default=0.00)
    chips_at_start = Column(Numeric(18, 2), nullable=False)
    chips_at_end = Column(Numeric(18, 2), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    has_folded = Column(Boolean, nullable=False, default=False)
    is_all_in = Column(Boolean, nullable=False, default=False)
    is_winner = Column(Boolean, nullable=False, default=False)
    hand_rank = Column(String(50), nullable=True)

    game = relationship("Game", back_populates="players")


class PlayerStatistics(Base):
    __tablename__ = "player_statistics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_hands = Column(Integer, nullable=False, default=0)
    hands_won = Column(Integer, nullable=False, default=0)
    total_winnings = Column(Numeric(18, 2), nullable=False, default=0.00)
    total_losses = Column(Numeric(18, 2), nullable=False, default=0.00)
    biggest_pot = Column(Numeric(18, 2), nullable=False, default=0.00)
    total_raises = Column(Integer, nullable=False, default=0)
    total_folds = Column(Integer, nullable=False, default=0)
    total_checks = Column(Integer, nullable=False, default=0)
    total_calls = Column(Integer, nullable=False, default=0)
    total_all_ins = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="player_statistics")


class GameHistory(Base):
    __tablename__ = "game_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    game_id = Column(BigInteger, ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    round_name = Column(String(50), nullable=False)
    action = Column(String(255), nullable=False)
    player_id = Column(BigInteger, nullable=True)
    amount = Column(Numeric(18, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    game = relationship("Game", back_populates="history")

    __table_args__ = (
        Index("idx_game_history_game_id", "game_id"),
    )
