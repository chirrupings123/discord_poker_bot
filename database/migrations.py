"""
Database migration script.

Run this to create all tables:

    python -m database.migrations

Or to run via the bot:

    python database/migrations.py
"""
import asyncio
from database.connection import init_db, close_db


async def run_migrations():
    print("Creating database tables...")
    await init_db()
    print("All tables created successfully.")


if __name__ == "__main__":
    asyncio.run(run_migrations())
