"""
Discord UI components for poker interactions.

Includes buttons for fold, check, call, raise, all-in,
and the main game embed builder.
"""
from __future__ import annotations

import math
from typing import Optional

import discord

from database.connection import async_session
from poker.game_manager import ActiveTable, active_tables


class PokerButton(discord.ui.Button["PokerView"]):
    def __init__(self, action: str, label: str, style: discord.ButtonStyle, row: int = 0, disabled: bool = False, amount: float = 0):
        super().__init__(label=label, style=style, row=row, disabled=disabled)
        self.action = action
        self.amount = amount

    async def callback(self, interaction: discord.Interaction):
        await self.view.handle_action(interaction, self.action, self.amount)


class PokerView(discord.ui.View):
    """
    A view that persists across interactions for a given table.
    Each table gets one view attached to the game message.
    """

    def __init__(self, table: ActiveTable, bot: discord.Client):
        super().__init__(timeout=None)
        self.table = table
        self.bot = bot
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()

        engine = self.table.engine
        if not engine or self.table.state != "playing":
            return

        current = engine.can_act_player()
        if not current:
            return

        can_check = engine.can_check()
        call_amount = engine.get_call_amount()
        min_raise = engine.get_min_raise()
        player_chips = current.chips

        can_fold = not can_check
        can_call = call_amount > 0 and player_chips > 0
        can_raise = player_chips > call_amount

        self.add_item(PokerButton("fold", "Fold", discord.ButtonStyle.danger, row=0, disabled=not can_fold))
        self.add_item(PokerButton("check", "Check", discord.ButtonStyle.secondary, row=0, disabled=not can_check))

        if can_call:
            call_label = f"Call ({call_amount:.0f})"
            self.add_item(PokerButton("call", call_label, discord.ButtonStyle.primary, row=0))
        else:
            self.add_item(PokerButton("call", "Call", discord.ButtonStyle.primary, row=0, disabled=True))

        if can_raise:
            raise_amount = min(min_raise, player_chips)
            self.add_item(PokerButton("raise", f"Raise ({raise_amount:.0f})", discord.ButtonStyle.success, row=1))
            if player_chips > raise_amount:
                pot_size = sum(p.amount for p in engine.pots)
                pot_raise = min(int(pot_size * 0.5), int(player_chips))
                if pot_raise > raise_amount:
                    self.add_item(PokerButton("raise", f"½ Pot ({pot_raise})", discord.ButtonStyle.success, row=1, amount=float(pot_raise)))
                all_in_amount = player_chips
                self.add_item(PokerButton("raise", f"All-In ({all_in_amount:.0f})", discord.ButtonStyle.success, row=1, amount=all_in_amount))
        else:
            self.add_item(PokerButton("raise", "Raise", discord.ButtonStyle.success, row=1, disabled=True))

    async def handle_action(self, interaction: discord.Interaction, action: str, amount: float):
        user_id = interaction.user.id
        if user_id not in self.table.seated_players:
            await interaction.response.send_message("You are not in this game.", ephemeral=True)
            return

        engine = self.table.engine
        if not engine:
            await interaction.response.send_message("No active hand.", ephemeral=True)
            return

        current = engine.can_act_player()
        if not current or current.user_id != user_id:
            await interaction.response.send_message("It's not your turn.", ephemeral=True)
            return

        async with self.table.action_lock:
            if action == "fold":
                result = engine.fold()
            elif action == "check":
                if not engine.can_check():
                    await interaction.response.send_message("Cannot check, there is a bet to call.", ephemeral=True)
                    return
                result = engine.check()
            elif action == "call":
                result = engine.call()
            elif action == "raise":
                if amount <= 0:
                    amount = engine.get_min_raise()
                if amount >= current.chips:
                    result = engine.all_in()
                else:
                    result = engine.raise_bet(amount)
            else:
                await interaction.response.send_message("Unknown action.", ephemeral=True)
                return

            if "error" in result:
                await interaction.response.send_message(f"Error: {result['error']}", ephemeral=True)
                return

            await interaction.response.defer()

            if self.table._turn_task:
                self.table._turn_task.cancel()

            if engine.hand_over:
                await self._finish_hand()
            else:
                await self._update_game_message()

    async def _update_game_message(self):
        try:
            embed = build_game_embed(self.table)
            self._build_buttons()
            channel = self.bot.get_channel(self.table.channel_id)
            if channel:
                msg = await channel.fetch_message(self._message_id)
                await msg.edit(embed=embed, view=self)
        except Exception:
            pass

    async def _finish_hand(self):
        from services.user_service import update_balance
        from database.connection import async_session
        from database.models import Game, GameStatus, TableStatus

        try:
            channel = self.bot.get_channel(self.table.channel_id)
            if not channel:
                return

            engine = self.table.engine
            embed = build_game_embed(self.table, show_winner=True)
            self.clear_items()
            view = discord.ui.View()
            btn = discord.ui.Button(label="Next Hand", style=discord.ButtonStyle.primary, custom_id=f"next_hand_{self.table.table_id}")
            btn_stop = discord.ui.Button(label="Stop Game", style=discord.ButtonStyle.danger, custom_id=f"stop_game_{self.table.table_id}")
            view.add_item(btn)
            view.add_item(btn_stop)

            try:
                msg = await channel.fetch_message(self._message_id)
                await msg.edit(embed=embed, view=view)
            except Exception:
                pass

            for player in engine.players_in_hand:
                net = player.net_won
                if abs(net) > 0.01:
                    async with async_session() as session:
                        await update_balance(
                            session, player.user_id, net,
                            "hand_won" if net > 0 else "hand_lost",
                        )

            self.table.state = "hand_complete"
        except Exception as e:
            print(f"Error finishing hand: {e}")


async def handle_next_hand(interaction: discord.Interaction, table_id: int):
    table = active_tables.get(table_id)
    if not table:
        await interaction.response.send_message("Table not found.", ephemeral=True)
        return

    if interaction.user.id != table.host_id:
        await interaction.response.send_message("Only the host can start the next hand.", ephemeral=True)
        return

    engine = table.start_new_hand()
    if engine is None:
        await interaction.response.send_message("Not enough active players to start a new hand.", ephemeral=True)
        return

    await interaction.response.defer()

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
                        ephemeral=False,
                    )
                    return

    view = PokerView(table, interaction.client)
    embed = build_game_embed(table)
    msg = await interaction.channel.send(embed=embed, view=view)
    view._message_id = msg.id


async def handle_stop_game(interaction: discord.Interaction, table_id: int):
    table = active_tables.get(table_id)
    if not table:
        await interaction.response.send_message("Table not found.", ephemeral=True)
        return

    if interaction.user.id != table.host_id:
        await interaction.response.send_message("Only the host can stop the game.", ephemeral=True)
        return

    from database.connection import async_session
    from services.poker_service import set_table_status
    from database.models import TableStatus

    async with async_session() as session:
        await set_table_status(session, table_id, TableStatus.FINISHED)

    active_tables.pop(table_id, None)

    embed = discord.Embed(
        title="🃏 Game Over",
        description="The table has been closed. Thanks for playing!",
        color=discord.Color.red(),
    )
    await interaction.response.edit_message(embed=embed, view=None)


def build_game_embed(table: ActiveTable, show_winner: bool = False) -> discord.Embed:
    engine = table.engine
    if not engine:
        return discord.Embed(title="No active hand", color=discord.Color.dark_gray())

    state = engine.public_state()
    total_pot = state["total_pot"]

    if engine.round.value == "showdown" or show_winner:
        color = discord.Color.gold()
    elif engine.round.value == "preflop":
        color = discord.Color.blue()
    elif engine.round.value == "flop":
        color = discord.Color.green()
    elif engine.round.value == "turn":
        color = discord.Color.orange()
    else:
        color = discord.Color.red()

    title = f"🃏 Table #{table.table_id} — Hand #{table.hand_number}"
    embed = discord.Embed(title=title, color=color)

    community = " ".join(state["community_cards"]) if state["community_cards"] else "None yet"
    embed.add_field(name="Community Cards", value=f"```{community}```", inline=False)

    embed.add_field(name="Pot", value=f"**{total_pot:.0f}** chips", inline=True)
    embed.add_field(name="Round", value=engine.round.value.upper(), inline=True)
    embed.add_field(name="Current Bet", value=f"{state['current_bet']:.0f}" if state["current_bet"] > 0 else "0", inline=True)

    players_info = []
    for p in state["players"]:
        if not p["is_active"]:
            continue
        name_str = f"<@{p['user_id']}>"
        if p["has_folded"]:
            name_str += " [FOLDED]"
        if p["is_all_in"]:
            name_str += " [ALL-IN]"
        if p.get("hand_rank"):
            name_str += f" — {p['hand_rank']}"
        if show_winner and p.get("hand_rank"):
            winner_info = f"💰 Won {p['net_won']:.0f} chip(s)" if abs(p.get("net_won", 0)) > 0.01 else ""
            players_info.append(f"{name_str}: {p['chips']:.0f} chips (bet: {p['total_bet']:.0f}) {winner_info}")
        else:
            players_info.append(f"{name_str}: {p['chips']:.0f} chips (bet: {p['total_bet']:.0f})")

    embed.add_field(name=f"Players ({len(players_info)})", value="\n".join(players_info) if players_info else "None", inline=False)

    if engine.can_act_player():
        current = engine.can_act_player()
        embed.add_field(
            name="Current Turn",
            value=f"<@{current.user_id}>",
            inline=False,
        )

    embed.set_footer(text=f"Buy-in: {table.buy_in:.0f} chips | Small Blind: {table.small_blind} | Big Blind: {table.big_blind}")

    return embed
