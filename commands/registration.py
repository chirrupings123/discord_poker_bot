import discord
from discord import app_commands
from discord.ext import commands

from database.connection import async_session
from services.user_service import register_user, get_user, get_balance, get_profile


def register_commands(bot: commands.Bot, guild: discord.Object | None):

    @bot.tree.command(name="register", description="Register for poker and receive starting chips", guild=guild)
    async def register(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with async_session() as session:
            result = await register_user(
                session,
                interaction.user.id,
                interaction.user.name,
                interaction.user.created_at,
            )
        await interaction.followup.send(result["message"], ephemeral=True)

    @bot.tree.command(name="balance", description="Check your chip balance", guild=guild)
    async def balance(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with async_session() as session:
            bal = await get_balance(session, interaction.user.id)
        if bal is None:
            await interaction.followup.send("You are not registered. Use `/register` first.", ephemeral=True)
        else:
            await interaction.followup.send(f"💰 **Your balance:** {bal:,.2f} chips", ephemeral=True)

    @bot.tree.command(name="profile", description="View your poker profile", guild=guild)
    async def profile(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with async_session() as session:
            profile_data = await get_profile(session, interaction.user.id)
        if profile_data is None:
            await interaction.followup.send("You are not registered. Use `/register` first.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🎴 {profile_data['username']}'s Profile",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Balance", value=f"{profile_data['balance']:,.2f} chips", inline=True)
        embed.add_field(name="Registered", value=f"<t:{int(profile_data['registered_at'].timestamp())}:R>", inline=True)
        embed.add_field(name="Hands Played", value=str(profile_data['total_hands_played']), inline=True)
        embed.add_field(name="Hands Won", value=str(profile_data['total_hands_won']), inline=True)
        embed.add_field(name="Biggest Pot", value=f"{profile_data['biggest_pot_won']:,.2f}", inline=True)
        embed.add_field(name="Lifetime Winnings", value=f"{profile_data['lifetime_winnings']:,.2f}", inline=True)
        embed.add_field(name="Lifetime Losses", value=f"{profile_data['lifetime_losses']:,.2f}", inline=True)
        embed.add_field(name="Rebuys Used", value=str(profile_data['rebuy_count']), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)
