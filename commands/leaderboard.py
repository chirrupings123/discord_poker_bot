import discord
from discord import app_commands
from discord.ext import commands

from database.connection import async_session
from services.user_service import get_leaderboard


def register_commands(bot: commands.Bot, guild: discord.Object | None):

    @bot.tree.command(name="leaderboard", description="View the poker leaderboards", guild=guild)
    @app_commands.describe(
        category="Leaderboard category: balance, hands_won, or biggest_pot"
    )
    @app_commands.choices(category=[
        app_commands.Choice(name="Richest Players", value="balance"),
        app_commands.Choice(name="Most Hands Won", value="hands_won"),
        app_commands.Choice(name="Biggest Pots", value="biggest_pot"),
    ])
    async def leaderboard(
        interaction: discord.Interaction,
        category: str = "balance",
    ):
        await interaction.response.defer(ephemeral=True)

        async with async_session() as session:
            entries = await get_leaderboard(session, sort_by=category, limit=10)

        if not entries:
            await interaction.followup.send("No registered players yet.", ephemeral=True)
            return

        titles = {
            "balance": "🏆 Richest Players",
            "hands_won": "🏆 Most Hands Won",
            "biggest_pot": "🏆 Biggest Pot Winners",
        }
        value_labels = {
            "balance": lambda e: f"{e['balance']:,.2f} chips",
            "hands_won": lambda e: f"{e['hands_won']} hands",
            "biggest_pot": lambda e: f"{e['biggest_pot']:,.2f} chips",
        }

        embed = discord.Embed(
            title=titles.get(category, "🏆 Leaderboard"),
            color=discord.Color.gold(),
        )

        lines = []
        for entry in entries:
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(entry["rank"], f"{entry['rank']}.")
            value = value_labels[category](entry)
            lines.append(f"{medal} <@{entry['user_id']}> — {value}")

        embed.description = "\n".join(lines)
        await interaction.followup.send(embed=embed, ephemeral=True)
