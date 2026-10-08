"""Discord bot entry point."""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import Config

# Import commands
from bot.commands import connect, teams, attendance, mmr_history, leaderboard, modify_mmr, help


class LeagueTeamBot(commands.Bot):
    """Main Discord bot class."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            description="League of Legends Team Generator Bot"
        )
    
    async def setup_hook(self):
        """Called when the bot is being set up."""
        # Register commands
        await self.add_cog(connect.ConnectCommand(self))
        await self.add_cog(teams.TeamsCommand(self))
        await self.add_cog(attendance.AttendanceCommand(self))
        await self.add_cog(mmr_history.MMRHistoryCommand(self))
        await self.add_cog(leaderboard.LeaderboardCommand(self))
        await self.add_cog(modify_mmr.ModifyMMRCommand(self))
        await self.add_cog(help.HelpCommand(self))
        
        # List all registered commands before syncing
        print("\n📋 Registered commands before sync:", flush=True)
        for cmd in self.tree.get_commands():
            print(f"   - {cmd.name} (type: {type(cmd).__name__})", flush=True)
            if hasattr(cmd, 'checks'):
                print(f"     Checks: {cmd.checks}", flush=True)
        
       # Sync commands to the tournament server
        # Sync commands to the tournament server
        try:
            guild = discord.Object(id=1553131073846911016)

            print("\n🔄 Syncing commands to tournament server...", flush=True)

            # Copy all commands currently registered in the bot
            # to this specific guild
            self.tree.clear_commands(guild=guild)
            self.tree.copy_global_to(guild=guild)

            print("📋 Guild commands before sync:", flush=True)
            for cmd in self.tree.get_commands(guild=guild):
                print(f"   - /{cmd.name}", flush=True)

            synced = await self.tree.sync(guild=guild)

            print(
                f"✅ Synced {len(synced)} command(s) to tournament server",
                flush=True
            )

            for cmd in synced:
                print(f"   - /{cmd.name} (ID: {cmd.id})", flush=True)

        except Exception as e:
            print(f"❌ Failed to sync commands: {e}", flush=True)
            import traceback
            traceback.print_exc()

        # Attach tree-level error handler (equivalent to @client.tree.error)
        async def _tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            # Unwrap original exception
            err = getattr(error, "original", error)

            # Ensure we always respond within the interaction window
            async def _safe_respond(message: str):
                if interaction.response.is_done():
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)

            if isinstance(err, app_commands.MissingPermissions):
                await _safe_respond("❌ You need **Administrator** to use this.")
                return

            if isinstance(err, (app_commands.MissingRole, app_commands.MissingAnyRole)):
                await _safe_respond("❌ You don’t have the required role.")
                return

            # Fallback generic handler
            try:
                await _safe_respond("⚠️ Something went wrong.")
            except Exception:
                pass

        # Register on_error handler on the tree
        self.tree.on_error = _tree_error
    
    async def on_ready(self):
        """Called when the bot is ready."""
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})", flush=True)
        print(f"✅ Bot is ready! Connected to {len(self.guilds)} guild(s)", flush=True)
        print(f"API Base URL: {Config.API_BASE_URL}", flush=True)
        print(f"FastAPI should be running at: {Config.API_BASE_URL}", flush=True)
        
        # List all commands in the tree
        print("\n📋 All commands in command tree:", flush=True)
        for cmd in self.tree.get_commands():
            checks_info = ""
            if hasattr(cmd, 'checks') and cmd.checks:
                checks_info = f" [has {len(cmd.checks)} check(s)]"
            print(f"   - /{cmd.name}{checks_info}", flush=True)
        

    
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return
        print(f"Error: {error}", flush=True)
        import traceback
        traceback.print_exc()
    
    async def on_interaction(self, interaction: discord.Interaction):
        """Log all interactions for debugging."""
        if interaction.type == discord.InteractionType.application_command:
            print(f"[Bot] Received command: {interaction.command.name if interaction.command else 'unknown'} from {interaction.user} ({interaction.user.id})", flush=True)
            if interaction.command and hasattr(interaction.command, 'checks') and interaction.command.checks:
                print(f"[Bot] Command has {len(interaction.command.checks)} permission check(s)", flush=True)
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handle application command errors."""
        print(f"[Bot] ========== ERROR HANDLER CALLED ==========", flush=True)
        print(f"[Bot] Command error in {interaction.command.name if interaction.command else 'unknown'}: {error}", flush=True)
        print(f"[Bot] Error type: {type(error).__name__}", flush=True)
        print(f"[Bot] Error class: {type(error)}", flush=True)
        print(f"[Bot] Is MissingPermissions? {isinstance(error, app_commands.MissingPermissions)}", flush=True)
        import traceback
        traceback.print_exc()
        
        # Try to send error message to user - ALWAYS respond to avoid timeout
        try:
            if isinstance(error, app_commands.MissingPermissions):
                print(f"[Bot] Handling MissingPermissions error", flush=True)
                # Log permission denial for auditing with detailed debug info
                user = interaction.user
                guild = interaction.guild
                member = guild.get_member(user.id) if guild else None
                
                print(f"[Bot] PERMISSION DENIED - User: {user} (ID: {user.id}) attempted to use {interaction.command.name if interaction.command else 'unknown'}", flush=True)
                print(f"[Bot]   - Guild: {guild.name if guild else 'DM'} (ID: {guild.id if guild else 'N/A'})", flush=True)
                if guild:
                    print(f"[Bot]   - Guild owner ID: {guild.owner_id}", flush=True)
                    print(f"[Bot]   - User ID: {user.id}", flush=True)
                    print(f"[Bot]   - Is owner: {user.id == guild.owner_id}", flush=True)
                if member:
                    print(f"[Bot]   - Member object found: {member}", flush=True)
                    print(f"[Bot]   - Member guild_permissions: {member.guild_permissions}", flush=True)
                    print(f"[Bot]   - Member has admin: {member.guild_permissions.administrator}", flush=True)
                    print(f"[Bot]   - Member top_role: {member.top_role}", flush=True)
                else:
                    print(f"[Bot]   - Member object NOT found (user might not be in guild cache)", flush=True)
                print(f"[Bot]   - User guild_permissions (from interaction): {user.guild_permissions if hasattr(user, 'guild_permissions') else 'N/A'}", flush=True)
                if hasattr(user, 'guild_permissions'):
                    print(f"[Bot]   - User has admin (from interaction): {user.guild_permissions.administrator}", flush=True)
                
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="You need **Administrator** permission to use this command.",
                    color=discord.Color.red()
                )
                
                # Always try to respond - check if already responded
                if not interaction.response.is_done():
                    print(f"[Bot] Sending permission denied response (response not done)", flush=True)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    print(f"[Bot] Response already done, sending followup", flush=True)
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Handle other errors
                error_msg = f"❌ Error: {str(error)}"
                if not interaction.response.is_done():
                    print(f"[Bot] Sending error response (response not done)", flush=True)
                    await interaction.response.send_message(error_msg, ephemeral=True)
                else:
                    print(f"[Bot] Response already done, sending error followup", flush=True)
                    await interaction.followup.send(error_msg, ephemeral=True)
        except Exception as e:
            print(f"[Bot] ERROR in error handler: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # Last resort - try to respond anyway
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
            except:
                pass


async def main():
    """Main function to run the bot."""
    # Force immediate output flushing
    sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None
    
    print("=" * 60, flush=True)
    print("Discord Bot Starting...", flush=True)
    print("=" * 60, flush=True)
    
    # Validate configuration
    try:
        print("Validating configuration...", flush=True)
        Config.validate()
        print("✅ Configuration valid", flush=True)
    except ValueError as e:
        print(f"❌ Configuration error: {e}", flush=True)
        print("Please check your .env file", flush=True)
        sys.exit(1)
    
    # Create and run bot
    print("Creating bot instance...", flush=True)
    bot = LeagueTeamBot()
    print("Bot instance created", flush=True)
    
    print(f"Attempting to connect with token: {Config.DISCORD_BOT_TOKEN[:10]}...", flush=True)
    
    try:
        print("Starting bot connection...", flush=True)
        await bot.start(Config.DISCORD_BOT_TOKEN)
    except discord.LoginFailure as e:
        print(f"❌ Invalid Discord bot token: {e}", flush=True)
        print("Please check your DISCORD_BOT_TOKEN in environment variables", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting bot: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("Bot shutting down...", flush=True)
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())

