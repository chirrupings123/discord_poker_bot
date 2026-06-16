#!/usr/bin/env python3
"""
Discord Poker Bot — main entry point.

Run with:
    python bot.py
"""
import asyncio
import logging

import discord
from discord.ext import commands

from config import Config
from database.connection import init_db, close_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("poker_bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=Config.DISCORD_APP_ID,
)

guild = discord.Object(id=Config.GUILD_ID) if Config.GUILD_ID else None


@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(f"Connected to {len(bot.guilds)} guild(s)")

    await init_db()
    log.info("Database initialized.")

    if guild:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        log.info(f"Commands synced to guild {guild.id}")
    else:
        await bot.tree.sync()
        log.info("Commands synced globally")

    log.info("Bot is ready!")


async def load_extensions():
    from commands.registration import register_commands as reg_cmds
    from commands.poker import register_commands as poker_cmds
    from commands.rebuy import register_commands as rebuy_cmds
    from commands.stats import register_commands as stats_cmds
    from commands.leaderboard import register_commands as lb_cmds

    reg_cmds(bot, guild)
    poker_cmds(bot, guild)
    rebuy_cmds(bot, guild)
    stats_cmds(bot, guild)
    lb_cmds(bot, guild)
    log.info("All commands registered.")


async def main():
    await load_extensions()

    try:
        await bot.start(Config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        pass
    finally:
        await close_db()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
