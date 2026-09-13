import discord
from discord import app_commands
from discord.ext import commands

class AdminCog(commands.Cog, name="Admin"):
    """Server administration, announcements, and role analytics."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Broadcast a formal announcement embed to a specific channel.")
    @app_commands.describe(
        channel="The channel where the announcement should be posted",
        message="The body content of the announcement",
        title="Title header for the announcement embed (optional)",
        ping="Optional ping mention for the announcement",
    )
    @app_commands.choices(
        ping=[
            app_commands.Choice(name="None", value="none"),
            app_commands.Choice(name="@everyone", value="everyone"),
            app_commands.Choice(name="@here", value="here"),
        ]
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        title: str = "📢 Server Announcement",
        ping: app_commands.Choice[str] | None = None,
    ):
        if not channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(f"❌ I don't have permission to send messages in {channel.mention}.", ephemeral=True)
            return

        embed = discord.Embed(
            title=title,
            description=message,
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=f"Announced by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        ping_text = None
        if ping and ping.value == "everyone":
            ping_text = "@everyone"
        elif ping and ping.value == "here":
            ping_text = "@here"

        await channel.send(content=ping_text, embed=embed)
        await interaction.response.send_message(f"✅ Announcement sent to {channel.mention}!", ephemeral=True)

    @app_commands.command(name="roleinfo", description="Get in-depth statistics and permissions for a role.")
    @app_commands.describe(role="The role to inspect")
    @app_commands.guild_only()
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        embed = discord.Embed(
            title=f"Role Info: {role.name}",
            color=role.color if role.color != discord.Color.default() else discord.Color.blurple(),
        )

        embed.add_field(name="🆔 Role ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="🎨 Color", value=f"`{str(role.color)}`", inline=True)
        embed.add_field(name="👥 Members", value=f"**{len(role.members)}** members", inline=True)
        embed.add_field(name="📊 Position", value=f"#{role.position}", inline=True)
        embed.add_field(name="🔔 Mentionable?", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="📌 Hoisted (Separated)?", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="📅 Created", value=discord.utils.format_dt(role.created_at, style="F"), inline=False)

        # Highlight key permissions
        key_perms = []
        if role.permissions.administrator:
            key_perms.append("Administrator")
        if role.permissions.manage_guild:
            key_perms.append("Manage Server")
        if role.permissions.manage_roles:
            key_perms.append("Manage Roles")
        if role.permissions.manage_channels:
            key_perms.append("Manage Channels")
        if role.permissions.kick_members:
            key_perms.append("Kick Members")
        if role.permissions.ban_members:
            key_perms.append("Ban Members")
        if role.permissions.manage_messages:
            key_perms.append("Manage Messages")
        if role.permissions.mention_everyone:
            key_perms.append("Mention Everyone")

        perms_str = ", ".join(key_perms) if key_perms else "Standard permissions"
        embed.add_field(name="🛡️ Key Permissions", value=perms_str, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="membercount", description="Display full server member count breakdown.")
    @app_commands.guild_only()
    async def membercount(self, interaction: discord.Interaction):
        guild = interaction.guild
        total = guild.member_count or len(guild.members)
        humans = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)

        embed = discord.Embed(
            title=f"👥 Member Count — {guild.name}",
            color=discord.Color.teal(),
        )
        embed.add_field(name="Total Members", value=f"**{total}**", inline=True)
        embed.add_field(name="Humans", value=f"**{humans}**", inline=True)
        embed.add_field(name="Bots", value=f"**{bots}**", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="say", description="Make the bot send a message in a channel.")
    @app_commands.describe(message="The message to send", channel="Target channel (defaults to current)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    async def say(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel | None = None):
        target = channel or interaction.channel
        if not target.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message("❌ I lack permission to send messages in that channel.", ephemeral=True)
            return

        await target.send(message)
        await interaction.response.send_message(f"✅ Sent message to {target.mention}!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
