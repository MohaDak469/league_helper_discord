
import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo

MAX_PLAYERS = 10
MIN_ROLES = 1
MAX_ROLES = 2

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

ROLES = [
    "TOP",
    "JUNGLE",
    "MID",
    "ADC",
    "SUPPORT",
]


class ScrimView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        # Joueurs inscrits par jour
        self.players = {
            day: set()
            for day in self.get_next_days()
        }

        # Rôles choisis : roles[day][user_id] = ["MID", "ADC"]
        self.roles = {
            day: {}
            for day in self.players
        }

        self.message = None

        for index, day in enumerate(self.players):
            display_name = (
                f"Demain - {day}"
                if index == 0
                else day
            )

            self.add_item(
                ScrimDayButton(
                    day=day,
                    display_name=display_name,
                    scrim_view=self,
                )
            )

        self.add_item(ScrimResetButton(self))

    @staticmethod
    def get_next_days():
        today = datetime.now(BRUSSELS_TZ).weekday()

        return [
            DAYS[(today + offset) % 7]
            for offset in range(1, 7)
        ]

    def update_embed(self):
        now = datetime.now(BRUSSELS_TZ)

        embed = discord.Embed(
            title="🏆 Disponibilités Scrim",
            description=(
                "Sélectionne les jours où tu es disponible.\n"
                "Tu peux choisir plusieurs jours.\n\n"
                "Après ton inscription, choisis tes rôles "
                "pour chaque journée.\n"
                "Utilise `/inscrits` pour consulter les inscrits."
            ),
            color=discord.Color.blue(),
        )

        for day in self.players:
            count = len(self.players[day])

            status = (
                "🔴 **Complet**"
                if count >= MAX_PLAYERS
                else "🟢 **Disponible**"
            )

            embed.add_field(
                name=f"📅 {day}",
                value=f"**{count}/{MAX_PLAYERS} joueurs** • {status}",
                inline=False,
            )

        embed.set_footer(
            text=(
                "Dernière mise à jour : "
                f"{now.strftime('%d/%m/%Y à %H:%M')} "
                "• Europe/Brussels"
            )
        )

        return embed

    async def refresh_message(self, interaction):
        if self.message is not None:
            try:
                await self.message.edit(
                    embed=self.update_embed(),
                    view=self,
                )
            except discord.HTTPException:
                pass


class ScrimDayButton(discord.ui.Button):
    def __init__(self, day, display_name, scrim_view):
        self.day = day
        self.scrim_view = scrim_view

        super().__init__(
            label=display_name,
            style=discord.ButtonStyle.primary,
            custom_id=f"scrim_day_{day.lower()}",
        )

    async def callback(self, interaction: discord.Interaction):
        view = self.scrim_view
        user_id = interaction.user.id
        players = view.players[self.day]

        # Si déjà inscrit, proposer la désinscription
        if user_id in players:
            view.players[self.day].remove(user_id)
            view.roles[self.day].pop(user_id, None)

            await interaction.response.edit_message(
                embed=view.update_embed(),
                view=view,
            )

            await interaction.followup.send(
                f"❌ Tu es désinscrit de **{self.day}**. "
                "Tes rôles pour cette journée ont été supprimés.",
                ephemeral=True,
            )
            return

        # Vérifier la limite
        if len(players) >= MAX_PLAYERS:
            await interaction.response.send_message(
                f"🔴 **{self.day} est complet (10/10).**",
                ephemeral=True,
            )
            return

        # Afficher le choix de rôles avant de confirmer l'inscription
        await interaction.response.send_message(
            content=(
                f"🎮 **Choisis tes rôles pour {self.day}**\n"
                "Sélectionne entre 1 et 2 rôles, puis confirme."
            ),
            view=RoleSelectionView(
                day=self.day,
                scrim_view=view,
                user_id=user_id,
            ),
            ephemeral=True,
        )


class RoleSelectionView(discord.ui.View):
    def __init__(self, day, scrim_view, user_id):
        super().__init__(timeout=180)

        self.day = day
        self.scrim_view = scrim_view
        self.user_id = user_id
        self.selected_roles = []

        self.add_item(RoleSelectMenu(self))

        self.add_item(RoleConfirmButton(self))
        self.add_item(RoleCancelButton())

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Ce menu appartient à un autre joueur.",
                ephemeral=True,
            )
            return False

        return True


class RoleSelectMenu(discord.ui.Select):
    def __init__(self, role_view):
        self.role_view = role_view

        options = [
            discord.SelectOption(
                label=role,
                value=role,
                description=f"Jouer au poste {role}",
            )
            for role in ROLES
        ]

        super().__init__(
            placeholder="Choisis 1 ou 2 rôles...",
            min_values=MIN_ROLES,
            max_values=MAX_ROLES,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.role_view.selected_roles = list(self.values)

        await interaction.response.edit_message(
            content=(
                f"🎮 **Rôles pour {self.role_view.day}**\n"
                f"Choix actuel : {', '.join(self.values)}\n\n"
                "Clique sur **Confirmer** pour terminer."
            ),
            view=self.role_view,
        )


class RoleConfirmButton(discord.ui.Button):
    def __init__(self, role_view):
        self.role_view = role_view

        super().__init__(
            label="Confirmer",
            emoji="✅",
            style=discord.ButtonStyle.success,
        )

    async def callback(self, interaction: discord.Interaction):
        print(f"[SCRIM] Confirmer cliqué par {interaction.user.id}", flush=True)
        view = self.role_view
        scrim = view.scrim_view
        user_id = view.user_id
        day = view.day

        if not view.selected_roles:
            await interaction.response.send_message(
                "❌ Choisis au moins un rôle avant de confirmer.",
                ephemeral=True,
            )
            return

        # Vérifier à nouveau la capacité du jour
        players = scrim.players[day]

        if user_id not in players and len(players) >= MAX_PLAYERS:
            await interaction.response.edit_message(
                content=f"🔴 **{day} est maintenant complet (10/10).**",
                view=None,
            )
            return

        print(f"[SCRIM] Inscription de {user_id} pour {day},"f"rôles={view.selected_roles}",flush=True,)
        # Finaliser l'inscription et sauvegarder les rôles en mémoire
        players.add(user_id)
        scrim.roles[day][user_id] = list(view.selected_roles)

        print(f"[SCRIM] Inscription enregistrée : "f"{len(players)}/{MAX_PLAYERS}",flush=True,)

        await interaction.response.edit_message(
            content=(
                f"✅ **Inscription confirmée pour {day} !**\n"
                f"Tes rôles : {', '.join(view.selected_roles)}"
            ),
            view=None,
        )

        await scrim.refresh_message(interaction)


class RoleCancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Annuler",
            emoji="✖️",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Inscription annulée. Tu n'as pas été ajouté à cette journée.",
            view=None,
        )


class ScrimResetButton(discord.ui.Button):
    def __init__(self, scrim_view):
        self.scrim_view = scrim_view

        super().__init__(
            label="Réinitialiser",
            emoji="🔄",
            style=discord.ButtonStyle.danger,
            custom_id="scrim_reset",
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Seuls les administrateurs peuvent réinitialiser le sondage.",
                ephemeral=True,
            )
            return

        for day in self.scrim_view.players:
            self.scrim_view.players[day].clear()
            self.scrim_view.roles[day].clear()

        await interaction.response.edit_message(
            embed=self.scrim_view.update_embed(),
            view=self.scrim_view,
        )

        await interaction.followup.send(
            "🔄 Le sondage et toutes les inscriptions ont été réinitialisés.",
            ephemeral=True,
        )


class InscritsView(discord.ui.View):
    def __init__(self, scrim_view, user_id):
        super().__init__(timeout=120)

        self.scrim_view = scrim_view
        self.user_id = user_id

        for day in scrim_view.players:
            self.add_item(InscritsDayButton(day, scrim_view))

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Utilise ta propre commande `/inscrits`.",
                ephemeral=True,
            )
            return False

        return True


class InscritsDayButton(discord.ui.Button):
    def __init__(self, day, scrim_view):
        self.day = day
        self.scrim_view = scrim_view

        count = len(scrim_view.players[day])

        super().__init__(
            label=f"{day} — {count}/10",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(self, interaction: discord.Interaction):
        day = self.day
        players = self.scrim_view.players[day]
        roles = self.scrim_view.roles[day]
        count = len(players)

        if players:
            player_list = "\n".join(
                f"👤 <@{player_id}> — "
                f"{', '.join(roles.get(player_id, [])) or 'Rôles non définis'}"
                for player_id in sorted(players)
            )
        else:
            player_list = "*Aucun joueur inscrit.*"

        status = "🔴 Complet" if count >= MAX_PLAYERS else "🟢 Disponible"

        embed = discord.Embed(
            title=f"📅 {day}",
            description=(
                f"**{count}/{MAX_PLAYERS} joueurs** • {status}\n\n"
                f"{player_list}"
            ),
            color=(
                discord.Color.red()
                if count >= MAX_PLAYERS
                else discord.Color.green()
            ),
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None,
        )


class AttendanceCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scrim_views = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ Attendance system loaded.", flush=True)

    @discord.app_commands.command(
        name="scrim",
        description="Afficher les disponibilités pour les prochains scrims.",
    )
    async def scrim(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Cette commande doit être utilisée sur le serveur Discord.",
                ephemeral=True,
            )
            return

        view = ScrimView()
        self.scrim_views[interaction.guild.id] = view

        await interaction.response.send_message(
            embed=view.update_embed(),
            view=view,
        )

        view.message = await interaction.original_response()

    @discord.app_commands.command(
        name="inscrits",
        description="Voir les joueurs inscrits pour chaque jour.",
    )
    async def inscrits(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Cette commande doit être utilisée sur le serveur Discord.",
                ephemeral=True,
            )
            return

        view = self.scrim_views.get(interaction.guild.id)

        if view is None:
            await interaction.response.send_message(
                "❌ Aucun sondage `/scrim` n'est actuellement actif.",
                ephemeral=True,
            )
            return

        view_inscrits = InscritsView(
            scrim_view=view,
            user_id=interaction.user.id,
        )

        await interaction.response.send_message(
            "📋 **Choisis un jour pour voir les joueurs inscrits :**",
            view=view_inscrits,
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(AttendanceCommand(bot))
