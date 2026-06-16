import discord
from discord import app_commands
from discord.ext import commands

from database.connection import async_session
from services.user_service import get_stats


def register_commands(bot: commands.Bot, guild: discord.Object | None):

    @bot.tree.command(name="stats", description="View your poker statistics", guild=guild)
    async def stats(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with async_session() as session:
            stats_data = await get_stats(session, interaction.user.id)

        if stats_data is None:
            await interaction.followup.send("You are not registered. Use `/register` first.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📊 {interaction.user.name}'s Poker Statistics",
            color=discord.Color.green(),
        )
        embed.add_field(name="Hands Played", value=str(stats_data["total_hands"]), inline=True)
        embed.add_field(name="Hands Won", value=str(stats_data["hands_won"]), inline=True)
        embed.add_field(name="Win Rate", value=f"{stats_data['win_rate']}%", inline=True)
        embed.add_field(name="Biggest Pot Won", value=f"{stats_data['biggest_pot']:,.2f}", inline=True)
        embed.add_field(name="Lifetime Winnings", value=f"{stats_data['lifetime_winnings']:,.2f}", inline=True)
        embed.add_field(name="Lifetime Losses", value=f"{stats_data['lifetime_losses']:,.2f}", inline=True)
        embed.add_field(name="Net Profit", value=f"{stats_data['net']:,.2f}", inline=True)
        embed.add_field(name="Rebuys Used", value=str(stats_data["rebuy_count"]), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)
