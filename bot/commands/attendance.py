import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo


MAX_PLAYERS = 10

BRUSSELS_TZ = ZoneInfo("Europe/Brussels")


DAYS = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}


class ScrimView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        self.players = {
            day: set()
            for day in DAYS.values()
        }

        # Calcul des 6 prochains jours
        today = datetime.now(BRUSSELS_TZ).weekday()

        next_days = []

        for i in range(1, 7):
            next_day = (today + i) % 7
            next_days.append(DAYS[next_day])

        # Création des boutons
        for index, day in enumerate(next_days):

            if index == 0:
                display_name = f"Demain - {day}"
            else:
                display_name = day

            self.add_item(
                ScrimDayButton(
                    day=day,
                    display_name=display_name,
                    scrim_view=self
                )
            )

        # Bouton reset
        self.add_item(
            ScrimResetButton(self)
        )

    def update_embed(self):

        now = datetime.now(BRUSSELS_TZ)

        embed = discord.Embed(
            title="🏆 Disponibilités Scrim",
            description=(
                "Sélectionne les jours où tu es disponible.\n"
                "Tu peux sélectionner **plusieurs jours**.\n\n"
                "Clique sur un jour pour t'inscrire ou te retirer.\n"
                "Utilise `/inscrits` pour voir les joueurs inscrits."
            ),
            color=discord.Color.blue()
        )

        for day in self.players:

            count = len(self.players[day])

            if count >= MAX_PLAYERS:
                status = "🔴 **Complet**"
            else:
                status = "🟢 **Disponible**"

            embed.add_field(
                name=f"📅 {day}",
                value=(
                    f"**{count}/{MAX_PLAYERS} joueurs** • {status}"
                ),
                inline=False
            )

        embed.set_footer(
            text=(
                f"Dernière mise à jour : "
                f"{now.strftime('%d/%m/%Y à %H:%M')} "
                f"• Europe/Brussels"
            )
        )

        return embed


class ScrimDayButton(discord.ui.Button):

    def __init__(
        self,
        day,
        display_name,
        scrim_view
    ):

        self.day = day
        self.scrim_view = scrim_view

        super().__init__(
            label=display_name,
            style=discord.ButtonStyle.primary,
            custom_id=f"scrim_day_{day.lower()}"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        players = self.scrim_view.players[self.day]

        user_id = interaction.user.id

        # ==========================================
        # DÉSINSCRIPTION
        # ==========================================

        if user_id in players:

            players.remove(user_id)

            await interaction.response.edit_message(
                embed=self.scrim_view.update_embed(),
                view=self.scrim_view
            )

            await interaction.followup.send(
                f"❌ Tu n'es plus inscrit pour **{self.day}**.",
                ephemeral=True
            )

            return

        # ==========================================
        # JOURNÉE COMPLÈTE
        # ==========================================

        if len(players) >= MAX_PLAYERS:

            await interaction.response.send_message(
                f"🔴 **{self.day} est complet (10/10).**",
                ephemeral=True
            )

            return

        # ==========================================
        # INSCRIPTION
        # ==========================================

        players.add(user_id)

        await interaction.response.edit_message(
            embed=self.scrim_view.update_embed(),
            view=self.scrim_view
        )

        await interaction.followup.send(
            f"✅ Tu es inscrit pour **{self.day}** !",
            ephemeral=True
        )


class ScrimResetButton(discord.ui.Button):

    def __init__(self, scrim_view):

        self.scrim_view = scrim_view

        super().__init__(
            label="Réinitialiser",
            emoji="🔄",
            style=discord.ButtonStyle.danger,
            custom_id="scrim_reset"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        # ==========================================
        # ADMIN UNIQUEMENT
        # ==========================================

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent "
                "réinitialiser le sondage.",
                ephemeral=True
            )

            return

        # ==========================================
        # RESET
        # ==========================================

        for day in self.scrim_view.players:
            self.scrim_view.players[day].clear()

        await interaction.response.edit_message(
            embed=self.scrim_view.update_embed(),
            view=self.scrim_view
        )

        await interaction.followup.send(
            "🔄 Le sondage des disponibilités "
            "a été réinitialisé.",
            ephemeral=True
        )


class AttendanceCommand(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # On garde une référence aux sondages actifs
        self.scrim_views = {}

    @commands.Cog.listener()
    async def on_ready(self):

        print("✅ Attendance system loaded.")

    # ==========================================
    # /scrim
    # ==========================================

    @discord.app_commands.command(
        name="scrim",
        description="Afficher les disponibilités pour les prochains scrims."
    )
    async def scrim(
        self,
        interaction: discord.Interaction
    ):

        view = ScrimView()

        self.scrim_views[interaction.guild.id] = view

        await interaction.response.send_message(
            embed=view.update_embed(),
            view=view
        )

    # ==========================================
    # /inscrits
    # ==========================================

    @discord.app_commands.command(
        name="inscrits",
        description="Voir les joueurs inscrits pour chaque jour."
    )
    async def inscrits(
        self,
        interaction: discord.Interaction
    ):

        view = self.scrim_views.get(
            interaction.guild.id
        )

        if view is None:

            await interaction.response.send_message(
                "❌ Aucun sondage `/scrim` n'est actuellement actif.",
                ephemeral=True
            )

            return

        # Créer une vue avec les 6 jours
        view_inscrits = InscritsView(view)

        await interaction.response.send_message(
            "📋 **Choisis un jour pour voir les joueurs inscrits :**",
            view=view_inscrits,
            ephemeral=True
        )


class InscritsView(discord.ui.View):

    def __init__(self, scrim_view):

        super().__init__(timeout=120)

        self.scrim_view = scrim_view

        for day in scrim_view.players:

            self.add_item(
                InscritsDayButton(
                    day,
                    scrim_view
                )
            )


class InscritsDayButton(discord.ui.Button):

    def __init__(
        self,
        day,
        scrim_view
    ):

        self.day = day
        self.scrim_view = scrim_view

        count = len(
            scrim_view.players[day]
        )

        super().__init__(
            label=f"{day} — {count}/10",
            style=discord.ButtonStyle.secondary
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        players = self.scrim_view.players[self.day]

        count = len(players)

        # ==========================================
        # LISTE DES JOUEURS
        # ==========================================

        if players:

            player_list = "\n".join(
                f"👤 <@{player_id}>"
                for player_id in players
            )

        else:

            player_list = "*Aucun joueur inscrit.*"

        # ==========================================
        # STATUT
        # ==========================================

        if count >= MAX_PLAYERS:

            status = "🔴 Complet"

        else:

            status = "🟢 Disponible"

        embed = discord.Embed(
            title=f"📅 {self.day}",
            description=(
                f"**{count}/{MAX_PLAYERS} joueurs** • {status}\n\n"
                f"{player_list}"
            ),
            color=(
                discord.Color.red()
                if count >= MAX_PLAYERS
                else discord.Color.green()
            )
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )


async def setup(bot):

    await bot.add_cog(
        AttendanceCommand(bot)
    )