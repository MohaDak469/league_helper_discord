"""Scrim registration command."""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
from typing import Set


MAX_PLAYERS = 10


class AttendanceView(View):
    """View with buttons for scrim registration."""

    def __init__(self):
        super().__init__(timeout=None)
        self.ready_players: Set[int] = set()

    def update_embed(self) -> discord.Embed:
        """Create updated embed with current player list."""

        player_count = len(self.ready_players)

        if player_count >= MAX_PLAYERS:
            status = "🔒 SCRIM FULL"
            description = "Registration is closed."
        else:
            status = f"🟢 Registration open — {player_count}/{MAX_PLAYERS}"
            description = "Click **I'm In** if you want to play."

        embed = discord.Embed(
            title="🏆 Scrim Registration",
            description=description,
            color=discord.Color.blue()
        )

        if self.ready_players:
            player_list = "\n".join(
                f"<@{user_id}>"
                for user_id in self.ready_players
            )

            embed.add_field(
                name=f"👥 Players ({player_count}/{MAX_PLAYERS})",
                value=player_list,
                inline=False
            )
        else:
            embed.add_field(
                name=f"👥 Players (0/{MAX_PLAYERS})",
                value="*Nobody has registered yet.*",
                inline=False
            )

        embed.add_field(
            name="📌 Status",
            value=status,
            inline=False
        )

        embed.set_footer(
            text=f"Last updated: {datetime.now().strftime('%H:%M')}"
        )

        return embed

    @discord.ui.button(
        label="I'm In 🎮",
        style=discord.ButtonStyle.success,
        custom_id="attendance_join"
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        """Handle player registration."""

        user_id = interaction.user.id

        if user_id in self.ready_players:
            await interaction.response.send_message(
                "❌ You are already registered for this scrim.",
                ephemeral=True
            )
            return

        if len(self.ready_players) >= MAX_PLAYERS:
            await interaction.response.send_message(
                "🔒 This scrim is full (10/10). Registration is closed.",
                ephemeral=True
            )
            return

        self.ready_players.add(user_id)

        embed = self.update_embed()

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

        await interaction.followup.send(
            f"✅ You are registered! "
            f"({len(self.ready_players)}/{MAX_PLAYERS})",
            ephemeral=True
        )

    @discord.ui.button(
        label="Leave ❌",
        style=discord.ButtonStyle.danger,
        custom_id="attendance_leave"
    )
    async def leave_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        """Handle player leaving."""

        user_id = interaction.user.id

        if user_id not in self.ready_players:
            await interaction.response.send_message(
                "❌ You are not registered for this scrim.",
                ephemeral=True
            )
            return

        self.ready_players.remove(user_id)

        embed = self.update_embed()

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

        await interaction.followup.send(
            "❌ You have been removed from the scrim.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Reset 🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="attendance_clear"
    )
    async def clear_button(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        """Handle resetting the registration list."""

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ Only moderators can reset the registration list.",
                ephemeral=True
            )
            return

        self.ready_players.clear()

        embed = self.update_embed()

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

        await interaction.followup.send(
            "🔄 Registration list has been reset.",
            ephemeral=True
        )


class AttendanceCommand(commands.Cog):
    """Command for creating a scrim registration."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="scrim",
        description="Create a scrim registration"
    )
    async def attendance_check(
        self,
        interaction: discord.Interaction
    ):
        """Create a scrim registration."""

        view = AttendanceView()
        embed = view.update_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view
        )


async def setup(bot: commands.Bot):
    """Setup function for the cog."""

    await bot.add_cog(AttendanceCommand(bot))