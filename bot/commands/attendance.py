"""Scrim availability command."""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Set

BRUSSELS_TZ = ZoneInfo("Europe/Brussels")

MAX_PLAYERS = 10

DAYS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


class ScrimView(View):
    """View for scrim day availability."""

    def __init__(self, days):
        super().__init__(timeout=None)

        # Each day has its own set of players
        self.players: Dict[str, Set[int]] = {
            day: set() for day in days
        }

        self.days = days

        # Create one button for each day
        for day in days:
            self.add_item(ScrimDayButton(day, self))

    def update_embed(self) -> discord.Embed:
        """Create the availability embed."""

        embed = discord.Embed(
            title="📅 Scrim Availability",
            description=(
                "Choose every day you can play.\n\n"
                "You can select multiple days."
            ),
            color=discord.Color.blue()
        )

        for day in self.days:
            player_count = len(self.players[day])

            if player_count >= MAX_PLAYERS:
                status = "🔒 FULL"
            else:
                status = f"🟢 {player_count}/{MAX_PLAYERS}"

            if self.players[day]:
                player_list = " ".join(
                    f"<@{user_id}>"
                    for user_id in self.players[day]
                )
            else:
                player_list = "*Nobody yet*"

            embed.add_field(
                name=f"📅 {day} — {status}",
                value=player_list,
                inline=False
            )

        embed.set_footer(
            text=f"Last updated: {datetime.now(BRUSSELS_TZ).strftime('%H:%M')}"
        )

        return embed

    async def refresh(self, interaction: discord.Interaction):
        """Update the Discord message."""

        await interaction.response.edit_message(
            embed=self.update_embed(),
            view=self
        )


class ScrimDayButton(Button):
    """Button for one specific day."""

    def __init__(self, day: str, view: ScrimView):
        self.day = day
        self.scrim_view = view

        super().__init__(
            label=day,
            style=discord.ButtonStyle.primary,
            custom_id=f"scrim_day_{day.lower()}"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle day selection."""

        user_id = interaction.user.id
        players = self.scrim_view.players[self.day]

        # Already registered → remove them
        if user_id in players:
            players.remove(user_id)

            await interaction.response.edit_message(
                embed=self.scrim_view.update_embed(),
                view=self.scrim_view
            )

            await interaction.followup.send(
                f"❌ Removed you from **{self.day}**.",
                ephemeral=True
            )

            return

        # Day is already full
        if len(players) >= MAX_PLAYERS:
            await interaction.response.send_message(
                f"🔒 **{self.day}** is already full (10/10).",
                ephemeral=True
            )
            return

        # Add player
        players.add(user_id)

        await interaction.response.edit_message(
            embed=self.scrim_view.update_embed(),
            view=self.scrim_view
        )

        await interaction.followup.send(
            f"✅ Added you to **{self.day}** "
            f"({len(players)}/{MAX_PLAYERS}).",
            ephemeral=True
        )


class ScrimCommand(commands.Cog):
    """Command for creating scrim availability."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="scrim",
        description="Create a scrim availability poll"
    )
    async def scrim(
        self,
        interaction: discord.Interaction
    ):
        """Create the weekly scrim availability poll."""
        BRUSSELS_TZ = ZoneInfo("Europe/Brussels")
        today = datetime.now(BRUSSELS_TZ).weekday()
        # Get the next 6 days
        days = []

        for i in range(1, 7):
            next_day = (today + i) % 7
            days.append(DAYS[next_day])

        view = ScrimView(days)
        embed = view.update_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view
        )


async def setup(bot: commands.Bot):
    """Setup the command."""

    await bot.add_cog(ScrimCommand(bot))