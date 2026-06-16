from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from database.connection import async_session
from services.user_service import get_user, update_balance


def register_commands(bot: commands.Bot, guild: discord.Object | None):

    @bot.tree.command(name="rebuy", description="Request a rebuy when your balance is zero", guild=guild)
    async def rebuy(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        async with async_session() as session:
            user = await get_user(session, interaction.user.id)
            if not user:
                await interaction.followup.send("You are not registered. Use `/register` first.", ephemeral=True)
                return

            balance = float(user.balance)
            if balance > 0:
                await interaction.followup.send(
                    f"You still have {balance:,.2f} chips. Rebuy is only available when your balance reaches zero.",
                    ephemeral=True,
                )
                return

            if user.last_rebuy_at:
                days_since = (datetime.now(timezone.utc) - user.last_rebuy_at).days
                if days_since < Config.REBUY_COOLDOWN_DAYS:
                    next_rebuy = user.last_rebuy_at + timedelta(days=Config.REBUY_COOLDOWN_DAYS)
                    await interaction.followup.send(
                        f"Rebuy is on cooldown. You can rebuy again <t:{int(next_rebuy.timestamp())}:R>.\n"
                        f"(Once every {Config.REBUY_COOLDOWN_DAYS} days)",
                        ephemeral=True,
                    )
                    return

            result = await update_balance(
                session, interaction.user.id,
                Config.REBUY_CHIPS,
                "rebuy",
            )

            if not result["success"]:
                await interaction.followup.send(f"Rebuy failed: {result['message']}", ephemeral=True)
                return

        await interaction.followup.send(
            f"✅ **Rebuy successful!** You received {Config.REBUY_CHIPS:,} chips.\n"
            f"Your new balance: {result['new_balance']:,.2f} chips.",
            ephemeral=True,
        )
