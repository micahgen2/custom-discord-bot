import re
from datetime import timedelta
import discord
from discord import app_commands
from discord.ext import commands

TIME_REGEX = re.compile(r"^(\d+)(s|m|h|d)$", re.IGNORECASE)

def parse_duration(duration_str: str) -> timedelta | None:
    match = TIME_REGEX.match(duration_str.strip())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2).lower()
    if unit == "s":
        return timedelta(seconds=val)
    elif unit == "m":
        return timedelta(minutes=val)
    elif unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    return None

class ModerationCog(commands.Cog, name="Moderation"):
    """Server moderation commands with permission checks and role-hierarchy safeguards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Purge recent messages in this channel.")
    @app_commands.describe(amount="Number of messages to delete (1 - 100)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ Amount must be between 1 and 100.", ephemeral=True)
            return

        bot_member = interaction.guild.me
        if not interaction.channel.permissions_for(bot_member).manage_messages:
            await interaction.response.send_message(
                "❌ I do not have permission to `Manage Messages` in this channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"🧹 Successfully cleared **{len(deleted)}** messages.",
            ephemeral=True,
        )

    @app_commands.command(name="timeout", description="Timeout (mute) a member for a specified duration.")
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration format: 30s, 5m, 2h, 1d (max 28d)",
        reason="Reason for timeout (optional)",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str | None = None,
    ):
        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot timeout yourself!", ephemeral=True)
            return

        if member.id == interaction.guild.owner_id:
            await interaction.response.send_message("❌ You cannot timeout the server owner.", ephemeral=True)
            return

        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.moderate_members:
            await interaction.response.send_message("❌ I do not have permission to `Timeout Members`.", ephemeral=True)
            return

        if interaction.user != interaction.guild.owner and member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("❌ You cannot timeout a user with an equal or higher role.", ephemeral=True)
            return

        if member.top_role >= bot_member.top_role:
            await interaction.response.send_message("❌ I cannot timeout a user with an equal or higher role than my own.", ephemeral=True)
            return

        delta = parse_duration(duration)
        if not delta:
            await interaction.response.send_message("❌ Invalid duration! Use formats like `30s`, `10m`, `2h`, or `1d`.", ephemeral=True)
            return

        if delta > timedelta(days=28):
            await interaction.response.send_message("❌ Duration cannot exceed 28 days (Discord limit).", ephemeral=True)
            return

        clean_reason = reason or "No reason provided."
        try:
            await member.timeout(delta, reason=f"By {interaction.user.name}: {clean_reason}")
            embed = discord.Embed(
                title="⏳ Member Timed Out",
                description=f"**{member.display_name}** was timed out for **{duration}** by {interaction.user.mention}.",
                color=discord.Color.yellow(),
            )
            embed.add_field(name="Reason", value=clean_reason)
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Failed to timeout member: {e}", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove a timeout from a member early.")
    @app_commands.describe(member="The member to untimeout", reason="Reason (optional)")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None):
        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.moderate_members:
            await interaction.response.send_message("❌ I do not have permission to `Timeout Members`.", ephemeral=True)
            return

        if not member.is_timed_out():
            await interaction.response.send_message("❌ That member is not currently timed out.", ephemeral=True)
            return

        clean_reason = reason or "Timeout removed by moderator."
        try:
            await member.timeout(None, reason=f"By {interaction.user.name}: {clean_reason}")
            embed = discord.Embed(
                title="🔊 Timeout Removed",
                description=f"Timeout removed from **{member.display_name}** by {interaction.user.mention}.",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Failed to remove timeout: {e}", ephemeral=True)

    @app_commands.command(name="slowmode", description="Set or disable slowmode for the current channel.")
    @app_commands.describe(seconds="Slowmode cooldown in seconds (0 to 21600, 0 to disable)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        if seconds < 0 or seconds > 21600:
            await interaction.response.send_message("❌ Seconds must be between 0 and 21600 (6 hours).", ephemeral=True)
            return

        bot_member = interaction.guild.me
        if not interaction.channel.permissions_for(bot_member).manage_channels:
            await interaction.response.send_message("❌ I do not have permission to `Manage Channels`.", ephemeral=True)
            return

        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message("🚀 Slowmode has been **disabled** for this channel.")
        else:
            await interaction.response.send_message(f"⏱️ Slowmode set to **{seconds} seconds** for this channel.")

    @app_commands.command(name="lock", description="Lock down this channel so members cannot send messages.")
    @app_commands.describe(reason="Reason for locking the channel (optional)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, reason: str | None = None):
        bot_member = interaction.guild.me
        if not interaction.channel.permissions_for(bot_member).manage_channels:
            await interaction.response.send_message("❌ I do not have permission to `Manage Channels`.", ephemeral=True)
            return

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=reason)

        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"This channel has been locked by {interaction.user.mention}." + (f"\n**Reason:** {reason}" if reason else ""),
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unlock", description="Unlock a previously locked channel.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        bot_member = interaction.guild.me
        if not interaction.channel.permissions_for(bot_member).manage_channels:
            await interaction.response.send_message("❌ I do not have permission to `Manage Channels`.", ephemeral=True)
            return

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None  # Reset to default/inherit
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"This channel has been unlocked by {interaction.user.mention}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(
        member="The member to kick",
        reason="Reason for kicking this member (optional)",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None):
        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot kick yourself!", ephemeral=True)
            return

        if member.id == interaction.guild.owner_id:
            await interaction.response.send_message("❌ You cannot kick the server owner.", ephemeral=True)
            return

        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.kick_members:
            await interaction.response.send_message("❌ I do not have the `Kick Members` permission.", ephemeral=True)
            return

        if interaction.user != interaction.guild.owner and member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ You cannot kick this user because their role is equal to or higher than yours.",
                ephemeral=True,
            )
            return

        if member.top_role >= bot_member.top_role:
            await interaction.response.send_message(
                "❌ I cannot kick this user because their top role is equal to or higher than my own top role.",
                ephemeral=True,
            )
            return

        clean_reason = reason or "No reason provided."
        try:
            try:
                await member.send(f"You have been kicked from **{interaction.guild.name}**.\n**Reason:** {clean_reason}")
            except discord.HTTPException:
                pass

            await member.kick(reason=f"By {interaction.user.name}: {clean_reason}")

            embed = discord.Embed(
                title="👢 Member Kicked",
                description=f"**{member.display_name}** (`{member.id}`) was kicked by {interaction.user.mention}.",
                color=discord.Color.orange(),
            )
            embed.add_field(name="Reason", value=clean_reason)
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Failed to kick member: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(
        member="The member to ban",
        reason="Reason for banning this member (optional)",
        delete_message_days="Number of days of message history to delete (0 to 7)",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str | None = None,
        delete_message_days: int = 0,
    ):
        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot ban yourself!", ephemeral=True)
            return

        if member.id == interaction.guild.owner_id:
            await interaction.response.send_message("❌ You cannot ban the server owner.", ephemeral=True)
            return

        bot_member = interaction.guild.me
        if not bot_member.guild_permissions.ban_members:
            await interaction.response.send_message("❌ I do not have the `Ban Members` permission.", ephemeral=True)
            return

        if interaction.user != interaction.guild.owner and member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ You cannot ban this user because their role is equal to or higher than yours.",
                ephemeral=True,
            )
            return

        if member.top_role >= bot_member.top_role:
            await interaction.response.send_message(
                "❌ I cannot ban this user because their top role is equal to or higher than my own top role.",
                ephemeral=True,
            )
            return

        delete_message_days = max(0, min(7, delete_message_days))
        clean_reason = reason or "No reason provided."

        try:
            try:
                await member.send(f"You have been banned from **{interaction.guild.name}**.\n**Reason:** {clean_reason}")
            except discord.HTTPException:
                pass

            await member.ban(reason=f"By {interaction.user.name}: {clean_reason}", delete_message_days=delete_message_days)

            embed = discord.Embed(
                title="🔨 Member Banned",
                description=f"**{member.display_name}** (`{member.id}`) was banned by {interaction.user.mention}.",
                color=discord.Color.red(),
            )
            embed.add_field(name="Reason", value=clean_reason)
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Failed to ban member: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
