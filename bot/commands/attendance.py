import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo

MAX_PLAYERS = 10

BRUSSELS_TZ = ZoneInfo("Europe/Brussels")

DAYS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


class ScrimView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        # Chaque jour contient un set de Discord IDs
        self.players = {
            day: set()
            for day in DAYS.values()
        }

        # Ajouter les 6 prochains jours
        today = datetime.now(BRUSSELS_TZ).weekday()

        next_days = []

        for i in range(1, 7):
            next_day = (today + i) % 7
            next_days.append(DAYS[next_day])

        for day in next_days:
            self.add_item(ScrimDayButton(day, self))

        # Bouton reset
        self.add_item(ScrimResetButton(self))

    def update_embed(self):
        now = datetime.now(BRUSSELS_TZ)

        embed = discord.Embed(
            title="🏆 Disponibilités Scrim",
            description=(
                "Clique sur les jours où tu peux jouer.\n"
                "Tu peux sélectionner plusieurs jours.\n\n"
                "⚠️ Maximum **10 joueurs par jour**."
            ),
            color=discord.Color.blue()
        )

        for day in self.players:
            count = len(self.players[day])

            if count >= MAX_PLAYERS:
                status = "🔴 COMPLET"
            else:
                status = "🟢 Disponible"

            embed.add_field(
                name=f"📅 {day}",
                value=f"**{count}/{MAX_PLAYERS}** joueurs\n{status}",
                inline=True
            )

        embed.set_footer(
            text=f"Dernière mise à jour : {now.strftime('%d/%m/%Y à %H:%M')} • Europe/Brussels"
        )

        return embed


class ScrimDayButton(discord.ui.Button):
    def __init__(self, day, scrim_view):
        self.day = day
        self.scrim_view = scrim_view

        super().__init__(
            label=day,
            style=discord.ButtonStyle.primary,
            custom_id=f"scrim_day_{day.lower()}"
        )

    async def callback(self, interaction: discord.Interaction):

        players = self.scrim_view.players[self.day]
        user_id = interaction.user.id

        # Le joueur est déjà inscrit → le retirer
        if user_id in players:
            players.remove(user_id)

            await interaction.response.edit_message(
                embed=self.scrim_view.update_embed(),
                view=self.scrim_view
            )

            await interaction.followup.send(
                f"❌ Tu es retiré de **{self.day}**.",
                ephemeral=True
            )

            return

        # Journée complète
        if len(players) >= MAX_PLAYERS:
            await interaction.response.send_message(
                f"❌ **{self.day}** est déjà complet (10/10).",
                ephemeral=True
            )
            return

        # Inscription
        players.add(user_id)

        await interaction.response.edit_message(
            embed=self.scrim_view.update_embed(),
            view=self.scrim_view
        )

        await interaction.followup.send(
            f"✅ Tu es inscrit pour **{self.day}**.",
            ephemeral=True
        )


class ScrimResetButton(discord.ui.Button):
    def __init__(self, scrim_view):
        self.scrim_view = scrim_view

        super().__init__(
            label="Reset",
            emoji="🔄",
            style=discord.ButtonStyle.danger,
            custom_id="scrim_reset"
        )

    async def callback(self, interaction: discord.Interaction):

        # Seulement les admins
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Tu dois être administrateur pour utiliser ce bouton.",
                ephemeral=True
            )
            return

        for day in self.scrim_view.players:
            self.scrim_view.players[day].clear()

        await interaction.response.edit_message(
            embed=self.scrim_view.update_embed(),
            view=self.scrim_view
        )

        await interaction.followup.send(
            "🔄 Le planning des disponibilités a été réinitialisé.",
            ephemeral=True
        )


class AttendanceCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Attendance system loaded.")

    @discord.app_commands.command(
        name="scrim",
        description="Afficher les disponibilités pour les prochains scrims."
    )
    async def scrim(self, interaction: discord.Interaction):

        view = ScrimView()

        embed = view.update_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view
        )


async def setup(bot):
    await bot.add_cog(AttendanceCommand(bot))