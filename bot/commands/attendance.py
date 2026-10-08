import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo


MAX_PLAYERS = 10

BRUSSELS_TZ = ZoneInfo("Europe/Brussels")


# Noms français des jours
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

        # Joueurs inscrits par jour
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
                display_name = f"Demain — {day}"
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

    def progress_bar(self, count):
        """
        Crée une barre de progression sur 10 cases.
        """

        filled = "▰" * count
        empty = "▱" * (MAX_PLAYERS - count)

        return filled + empty

    def update_embed(self):

        now = datetime.now(BRUSSELS_TZ)

        embed = discord.Embed(
            title="🏆 Disponibilités Scrim",
            description=(
                "Sélectionne les jours où tu es disponible.\n"
                "Tu peux choisir **plusieurs jours**.\n\n"
                "🟢 Disponible = moins de 10 joueurs\n"
                "🔴 Complet = 10/10 joueurs\n\n"
                "Clique sur la barre d'un jour pour "
                "**t'inscrire ou te retirer**."
            ),
            color=discord.Color.blue()
        )

        for day in self.players:

            count = len(self.players[day])

            # Pourcentage
            percentage = int((count / MAX_PLAYERS) * 100)

            # Barre
            bar = self.progress_bar(count)

            # Statut
            if count >= MAX_PLAYERS:
                status = "🔴 **COMPLET**"
            else:
                status = "🟢 **Disponible**"

            # Liste des joueurs
            if count > 0:

                player_list = "\n".join(
                    f"👤 <@{player_id}>"
                    for player_id in self.players[day]
                )

            else:
                player_list = "*Aucun joueur inscrit*"

            embed.add_field(
                name=f"📅 {day}",
                value=(
                    f"`{bar}` **{percentage}%**\n"
                    f"**{count}/{MAX_PLAYERS} joueurs** • {status}\n\n"
                    f"{player_list}"
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
        self.display_name = display_name
        self.scrim_view = scrim_view

        count = len(scrim_view.players[day])

        # Barre affichée sur le bouton
        filled = "▰" * count
        empty = "▱" * (MAX_PLAYERS - count)

        bar = filled + empty

        if count >= MAX_PLAYERS:
            style = discord.ButtonStyle.danger
        else:
            style = discord.ButtonStyle.primary

        super().__init__(
            label=f"{display_name} • {bar} {count}/{MAX_PLAYERS}",
            style=style,
            custom_id=f"scrim_day_{day.lower()}"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        players = self.scrim_view.players[self.day]

        user_id = interaction.user.id

        # ==========================================
        # JOUEUR DÉJÀ INSCRIT
        # ==========================================

        if user_id in players:

            players.remove(user_id)

            await interaction.response.edit_message(
                embed=self.scrim_view.update_embed(),
                view=self.scrim_view
            )

            # Liste actuelle
            if players:

                player_list = "\n".join(
                    f"👤 <@{player_id}>"
                    for player_id in players
                )

            else:

                player_list = "*Aucun joueur inscrit*"

            await interaction.followup.send(
                (
                    f"❌ Tu n'es plus inscrit pour **{self.day}**.\n\n"
                    f"**{len(players)}/{MAX_PLAYERS} joueurs**\n\n"
                    f"{player_list}"
                ),
                ephemeral=True
            )

            return

        # ==========================================
        # JOURNÉE COMPLÈTE
        # ==========================================

        if len(players) >= MAX_PLAYERS:

            player_list = "\n".join(
                f"👤 <@{player_id}>"
                for player_id in players
            )

            await interaction.response.send_message(
                (
                    f"🔴 **{self.day} est complet !**\n\n"
                    f"**10/{MAX_PLAYERS} joueurs**\n\n"
                    f"{player_list}"
                ),
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

        # Liste actuelle
        player_list = "\n".join(
            f"👤 <@{player_id}>"
            for player_id in players
        )

        await interaction.followup.send(
            (
                f"✅ Tu es inscrit pour **{self.day}** !\n\n"
                f"**{len(players)}/{MAX_PLAYERS} joueurs**\n\n"
                f"{player_list}"
            ),
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
        # VÉRIFICATION ADMIN
        # ==========================================

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent réinitialiser le sondage.",
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
            "🔄 Le sondage des disponibilités a été réinitialisé.",
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
    async def scrim(
        self,
        interaction: discord.Interaction
    ):

        view = ScrimView()

        embed = view.update_embed()

        await interaction.response.send_message(
            embed=embed,
            view=view
        )


async def setup(bot):

    await bot.add_cog(
        AttendanceCommand(bot)
    )