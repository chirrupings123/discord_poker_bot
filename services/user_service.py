from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from database.models import User, Transaction, PlayerStatistics


async def register_user(
    session: AsyncSession,
    user_id: int,
    username: str,
    discord_created_at: datetime,
) -> dict:
    existing = await session.get(User, user_id)
    if existing:
        return {"success": False, "message": "You are already registered."}

    account_age = (datetime.now(timezone.utc) - discord_created_at).days
    if account_age < Config.MIN_ACCOUNT_AGE_DAYS:
        return {
            "success": False,
            "message": (
                f"Your Discord account must be at least "
                f"{Config.MIN_ACCOUNT_AGE_DAYS} days old to register. "
                f"Your account is {account_age} day(s) old."
            ),
        }

    user = User(
        id=user_id,
        username=username,
        balance=Config.DEFAULT_STARTING_CHIPS,
        registered_at=datetime.now(timezone.utc),
    )
    session.add(user)

    txn = Transaction(
        user_id=user_id,
        amount=Config.DEFAULT_STARTING_CHIPS,
        reason="registration_bonus",
    )
    session.add(txn)

    stats = PlayerStatistics(user_id=user_id)
    session.add(stats)

    await session.commit()
    return {
        "success": True,
        "message": f"Registration successful! You received {Config.DEFAULT_STARTING_CHIPS:,} chips.",
    }


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_balance(session: AsyncSession, user_id: int) -> float | None:
    user = await session.get(User, user_id)
    if not user:
        return None
    return float(user.balance)


async def update_balance(
    session: AsyncSession,
    user_id: int,
    delta: float,
    reason: str,
    game_id: int | None = None,
) -> dict:
    user = await session.get(User, user_id)
    if not user:
        return {"success": False, "message": "User not found."}

    new_balance = float(user.balance) + delta
    if new_balance < 0:
        return {"success": False, "message": "Insufficient chips."}

    user.balance = new_balance

    if delta > 0:
        user.lifetime_winnings = float(user.lifetime_winnings) + delta
    else:
        user.lifetime_losses = float(user.lifetime_losses) + abs(delta)

    txn = Transaction(
        user_id=user_id,
        amount=delta,
        reason=reason,
        game_id=game_id,
    )
    session.add(txn)

    if reason == "rebuy":
        user.rebuy_count = (user.rebuy_count or 0) + 1
        user.last_rebuy_at = datetime.now(timezone.utc)

    await session.commit()
    return {"success": True, "new_balance": new_balance}


async def get_leaderboard(
    session: AsyncSession,
    sort_by: str = "balance",
    limit: int = 10,
) -> list[dict]:
    if sort_by == "hands_won":
        order_col = User.total_hands_won
    elif sort_by == "biggest_pot":
        order_col = User.biggest_pot_won
    else:
        order_col = User.balance

    result = await session.execute(
        select(User)
        .where(User.is_banned == False)
        .order_by(desc(order_col))
        .limit(limit)
    )
    users = result.scalars().all()

    return [
        {
            "rank": i + 1,
            "user_id": u.id,
            "username": u.username,
            "balance": float(u.balance),
            "hands_won": u.total_hands_won,
            "biggest_pot": float(u.biggest_pot_won),
        }
        for i, u in enumerate(users)
    ]


async def get_profile(session: AsyncSession, user_id: int) -> dict | None:
    user = await session.get(User, user_id)
    if not user:
        return None
    return {
        "user_id": user.id,
        "username": user.username,
        "balance": float(user.balance),
        "registered_at": user.registered_at,
        "rebuy_count": user.rebuy_count,
        "last_rebuy_at": user.last_rebuy_at,
        "total_hands_played": user.total_hands_played,
        "total_hands_won": user.total_hands_won,
        "biggest_pot_won": float(user.biggest_pot_won),
        "lifetime_winnings": float(user.lifetime_winnings),
        "lifetime_losses": float(user.lifetime_losses),
    }


async def get_stats(session: AsyncSession, user_id: int) -> dict | None:
    user = await session.get(User, user_id)
    if not user:
        return None

    win_rate = 0
    if user.total_hands_played > 0:
        win_rate = round(user.total_hands_won / user.total_hands_played * 100, 1)

    net = float(user.lifetime_winnings) - float(user.lifetime_losses)
    return {
        "total_hands": user.total_hands_played,
        "hands_won": user.total_hands_won,
        "win_rate": win_rate,
        "biggest_pot": float(user.biggest_pot_won),
        "lifetime_winnings": float(user.lifetime_winnings),
        "lifetime_losses": float(user.lifetime_losses),
        "net": net,
        "rebuy_count": user.rebuy_count,
    }
