import discord
from discord import app_commands
from discord.ext import commands

from database.connection import async_session
from database.models import TableStatus, GameTable
from services.user_service import get_user, update_balance
from services.poker_service import create_table_db, set_table_status, create_game_record, save_game_player, log_action
from poker.game_manager import create_table, get_table, list_tables, remove_table, ActiveTable
from views.poker_views import PokerView, build_game_embed, handle_next_hand, handle_stop_game
from config import Config


def register_commands(bot: commands.Bot, guild: discord.Object | None):

    @bot.tree.command(name="poker", description="Poker table commands", guild=guild)
    @app_commands.describe(
        action="create, list, join, leave, start",
        buyin="Buy-in amount (for create)",
        table_id="Table ID (for join)",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="create", value="create"),
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="join", value="join"),
        app_commands.Choice(name="leave", value="leave"),
        app_commands.Choice(name="start", value="start"),
    ])
    async def poker(
        interaction: discord.Interaction,
        action: str,
        buyin: int = None,
        table_id: int = None,
    ):
        if action == "create":
            await _create(interaction, buyin)
        elif action == "list":
            await _list(interaction)
        elif action == "join":
            await _join(interaction, table_id)
        elif action == "leave":
            await _leave(interaction)
        elif action == "start":
            await _start(interaction)

    async def _create(interaction: discord.Interaction, buyin: int | None):
        if buyin is None or buyin < 100:
            await interaction.response.send_message(
                "Please specify a buy-in amount (minimum 100 chips).\nExample: `/poker create buyin:1000`",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        async with async_session() as session:
            user = await get_user(session, interaction.user.id)
            if not user:
                await interaction.followup.send("You are not registered. Use `/register` first.", ephemeral=True)
                return

            if float(user.balance) < buyin:
                await interaction.followup.send(
                    f"Insufficient chips. You have {float(user.balance):,.2f} but need {buyin:,.0f}.",
                    ephemeral=True,
                )
                return

            table_db = await create_table_db(
                session,
                interaction.channel_id,
                interaction.guild_id,
                interaction.user.id,
                buyin,
            )

        table = create_table(
            table_id=table_db.id,
            channel_id=interaction.channel_id,
            guild_id=interaction.guild_id,
            host_id=interaction.user.id,
            buy_in=buyin,
        )

        table.add_player(interaction.user.id, buyin)

        await interaction.followup.send(
            f"✅ **Poker table #{table_db.id} created!**\n"
            f"Buy-in: {buyin:,} chips\n"
            f"Host: {interaction.user.mention}\n"
            f"Use `/poker join table_id:{table_db.id}` to join.\n"
            f"Use `/poker start` when ready (minimum 2 players).",
            ephemeral=False,
        )

    async def _list(interaction: discord.Interaction):
        tables = list_tables()
        if not tables:
            await interaction.response.send_message("No active tables. Create one with `/poker create buyin:1000`", ephemeral=True)
            return

        embed = discord.Embed(title="🎲 Active Poker Tables", color=discord.Color.blue())
        for t in tables:
            embed.add_field(
                name=f"Table #{t.table_id}",
                value=(
                    f"Host: <@{t.host_id}>\n"
                    f"Players: {t.player_count}/{t.max_players}\n"
                    f"Buy-in: {t.buy_in:,.0f}\n"
                    f"Status: {t.state.value}"
                ),
                inline=True,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _join(interaction: discord.Interaction, table_id: int | None):
        if table_id is None:
            await interaction.response.send_message("Please specify a table ID: `/poker join table_id:1`", ephemeral=True)
            return

        table = get_table(table_id)
        if not table:
            await interaction.response.send_message("Table not found.", ephemeral=True)
            return

        if table.state.value != "waiting":
            await interaction.response.send_message("This table is already in a game.", ephemeral=True)
            return

        if interaction.user.id in table.seated_players:
            await interaction.response.send_message("You are already at this table.", ephemeral=True)
            return

        if len(table.seated_players) >= table.max_players:
            await interaction.response.send_message("Table is full.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        async with async_session() as session:
            user = await get_user(session, interaction.user.id)
            if not user:
                await interaction.followup.send("You are not registered. Use `/register` first.", ephemeral=True)
                return

            if float(user.balance) < table.buy_in:
                await interaction.followup.send(
                    f"Insufficient chips. You have {float(user.balance):,.2f} but the buy-in is {table.buy_in:,.0f}.",
                    ephemeral=True,
                )
                return

            await update_balance(
                session, interaction.user.id, -table.buy_in,
                f"buy_in_table_{table_id}",
            )

        table.add_player(interaction.user.id, table.buy_in)

        await interaction.followup.send(
            f"✅ You joined **Table #{table_id}** with a {table.buy_in:,.0f} chip buy-in.",
            ephemeral=True,
        )

        channel = bot.get_channel(table.channel_id)
        if channel:
            msg = await channel.send(f"🎴 {interaction.user.mention} joined Table #{table_id}! ({table.player_count}/{table.max_players})")
            if table.player_count >= Config.MIN_PLAYERS:
                await channel.send(f"Table #{table_id} has {table.player_count} players! Host can `/poker start` to begin.")

    async def _leave(interaction: discord.Interaction):
        for tid, table in list(dict(list_tables()).items() if hasattr(list_tables(), 'items') else []):
            pass

        found = None
        for tid, tbl in [(t.table_id, t) for t in list_tables()]:
            if interaction.user.id in tbl.seated_players:
                found = tbl
                break

        if not found:
            await interaction.response.send_message("You are not at any table.", ephemeral=True)
            return

        if found.state.value != "waiting":
            await interaction.response.send_message("Cannot leave while a game is in progress.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        async with async_session() as session:
            await update_balance(
                session, interaction.user.id, found.buy_in,
                f"buy_in_refund_table_{found.table_id}",
            )

        found.remove_player(interaction.user.id)
        if found.player_count == 0:
            remove_table(found.table_id)
            async with async_session() as session:
                await set_table_status(session, found.table_id, TableStatus.FINISHED)

        await interaction.followup.send(
            f"✅ You left Table #{found.table_id}. Your buy-in of {found.buy_in:,.0f} chips has been refunded.",
            ephemeral=True,
        )

        channel = bot.get_channel(found.channel_id)
        if channel:
            await channel.send(f"🚪 {interaction.user.mention} left Table #{found.table_id}.")

    async def _start(interaction: discord.Interaction):
        table = None
        for t in list_tables():
            if t.host_id == interaction.user.id or interaction.user.id in t.seated_players:
                table = t
                break

        if not table:
            await interaction.response.send_message("You are not at any table.", ephemeral=True)
            return

        if interaction.user.id != table.host_id:
            await interaction.response.send_message("Only the host can start the game.", ephemeral=True)
            return

        if not table.can_start():
            await interaction.response.send_message(
                f"Need at least {Config.MIN_PLAYERS} players to start. Currently: {table.player_count}",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        async with async_session() as session:
            await set_table_status(session, table.table_id, TableStatus.PLAYING)

        table.state = "playing"

        engine = table.start_new_hand()
        if engine is None:
            await interaction.followup.send("Failed to start hand. Not enough players with chips.", ephemeral=True)
            return

        for uid, player in table.seated_players.items():
            if player.chips > 0:
                user = interaction.client.get_user(uid)
                if user:
                    try:
                        hole = " ".join(str(c) for c in player.hole_cards)
                        await user.send(f"**Your hole cards:** {hole}")
                    except discord.Forbidden:
                        await interaction.followup.send(
                            f"{user.mention}, I couldn't DM you your cards. Please enable DMs from server members.",
                        )
                        return

        view = PokerView(table, interaction.client)
        embed = build_game_embed(table)
        msg = await interaction.channel.send(embed=embed, view=view)
        view._message_id = msg.id

        await interaction.followup.send(f"🃏 **Game started at Table #{table.table_id}!**")
