import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_APP_ID: str = os.getenv("DISCORD_APP_ID", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://poker_user:poker_password@localhost:5432/poker_bot",
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql+psycopg2://poker_user:poker_password@localhost:5432/poker_bot",
    )
    GUILD_ID: int = int(os.getenv("GUILD_ID", "0"))

    DEFAULT_STARTING_CHIPS: int = int(os.getenv("DEFAULT_STARTING_CHIPS", "10000"))
    REBUY_CHIPS: int = int(os.getenv("REBUY_CHIPS", "5000"))
    REBUY_COOLDOWN_DAYS: int = int(os.getenv("REBUY_COOLDOWN_DAYS", "7"))
    MIN_ACCOUNT_AGE_DAYS: int = int(os.getenv("MIN_ACCOUNT_AGE_DAYS", "30"))

    SMALL_BLIND: int = 10
    BIG_BLIND: int = 20
    MIN_PLAYERS: int = 2
    MAX_PLAYERS: int = 9
