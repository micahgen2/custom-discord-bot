import logging
import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("DiscordBot.Events")

class EventsCog(commands.Cog, name="Events"):
    """Event listeners for bot lifecycle, member join, and app command error handling."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Register tree error handler
        self.bot.tree.on_error = self.on_app_command_error

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Bot successfully logged in as: {self.bot.user} (ID: {self.bot.user.id})")
        logger.info(f"Connected to {len(self.bot.guilds)} server(s)")

        # Update bot status / rich presence
        status_text = f"/help | in {len(self.bot.guilds)} server{'s' if len(self.bot.guilds) != 1 else ''}"
        activity = discord.Activity(type=discord.ActivityType.watching, name=status_text)
        await self.bot.change_presence(activity=activity, status=discord.Status.online)
        logger.info(f"Status updated to: Watching {status_text}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        status_text = f"/help | in {len(self.bot.guilds)} server{'s' if len(self.bot.guilds) != 1 else ''}"
        activity = discord.Activity(type=discord.ActivityType.watching, name=status_text)
        await self.bot.change_presence(activity=activity)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")
        status_text = f"/help | in {len(self.bot.guilds)} server{'s' if len(self.bot.guilds) != 1 else ''}"
        activity = discord.Activity(type=discord.ActivityType.watching, name=status_text)
        await self.bot.change_presence(activity=activity)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Sends a welcome message in the server's system channel if one is designated."""
        channel = member.guild.system_channel
        if channel and channel.permissions_for(member.guild.me).send_messages:
            embed = discord.Embed(
                title=f"👋 Welcome to {member.guild.name}!",
                description=f"Welcome {member.mention}! We're thrilled to have you here.\nUse `/help` to see what I can do.",
                color=discord.Color.green(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{member.guild.member_count}")
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as e:
                logger.warning(f"Could not send welcome message in {member.guild.name}: {e}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Global error handler for slash commands."""
        if isinstance(error, app_commands.MissingPermissions):
            missing = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
            message = f"🚫 You need the following permission(s) to use this command: {missing}"
        elif isinstance(error, app_commands.BotMissingPermissions):
            missing = ", ".join(f"`{perm}`" for perm in error.missing_permissions)
            message = f"🚫 I need the following permission(s) to execute this command: {missing}"
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = f"⏳ This command is on cooldown. Please wait `{error.retry_after:.1f}` seconds."
        elif isinstance(error, app_commands.CheckFailure):
            message = "❌ You cannot execute this command here."
        else:
            logger.error(f"Unhandled app command error in /{interaction.command.name if interaction.command else 'unknown'}: {error}", exc_info=True)
            message = "⚠️ An unexpected error occurred while processing this command."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
