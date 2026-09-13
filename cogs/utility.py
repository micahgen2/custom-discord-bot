import platform
import sys
import time
import discord
from discord import app_commands
from discord.ext import commands

class UtilityCog(commands.Cog, name="Utility"):
    """General utility and informative commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="ping", description="Check bot latency and response time.")
    async def ping(self, interaction: discord.Interaction):
        start_time = time.monotonic()
        await interaction.response.defer(ephemeral=False)
        end_time = time.monotonic()

        round_trip_ms = round((end_time - start_time) * 1000)
        ws_latency_ms = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.brand_green(),
        )
        embed.add_field(name="API Round-trip", value=f"`{round_trip_ms} ms`", inline=True)
        embed.add_field(name="Websocket Heartbeat", value=f"`{ws_latency_ms} ms`", inline=True)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="serverinfo", description="Display detailed information about this server.")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
            return

        total_members = guild.member_count or len(guild.members)
        humans = sum(1 for m in guild.members if not m.bot)
        bots = sum(1 for m in guild.members if m.bot)

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        role_count = len(guild.roles)

        embed = discord.Embed(
            title=guild.name,
            description=guild.description or "No description provided.",
            color=discord.Color.blurple(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(name="👑 Server Owner", value=f"{guild.owner.mention if guild.owner else 'Unknown'}", inline=True)
        embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 Created On", value=discord.utils.format_dt(guild.created_at, style="D"), inline=True)

        embed.add_field(
            name="👥 Members",
            value=f"Total: **{total_members}**\nHumans: **{humans}** | Bots: **{bots}**",
            inline=True,
        )
        embed.add_field(
            name="💬 Channels",
            value=f"Text: **{text_channels}** | Voice: **{voice_channels}**\nCategories: **{categories}**",
            inline=True,
        )
        embed.add_field(name="🛡️ Roles", value=f"**{role_count}** roles", inline=True)

        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="View account details of yourself or another member.")
    @app_commands.describe(user="The server member to inspect (defaults to you)")
    @app_commands.guild_only()
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member | None = None):
        target = user or interaction.user
        if not isinstance(target, discord.Member):
            target = await interaction.guild.fetch_member(target.id) if interaction.guild else target

        embed = discord.Embed(
            title=f"User Info: {target.display_name}",
            color=target.color if target.color != discord.Color.default() else discord.Color.blue(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="👤 Username", value=f"{target.name}", inline=True)
        embed.add_field(name="🆔 User ID", value=f"`{target.id}`", inline=True)
        embed.add_field(name="🤖 Bot?", value="Yes" if target.bot else "No", inline=True)

        embed.add_field(name="📅 Account Created", value=discord.utils.format_dt(target.created_at, style="F"), inline=False)
        if isinstance(target, discord.Member) and target.joined_at:
            embed.add_field(name="📥 Joined Server", value=discord.utils.format_dt(target.joined_at, style="F"), inline=False)

            roles = [r.mention for r in reversed(target.roles[1:])]  # omit @everyone
            roles_str = ", ".join(roles[:15]) if roles else "None"
            if len(roles) > 15:
                roles_str += f" and {len(roles) - 15} more..."
            embed.add_field(name=f"🛡️ Roles [{len(roles)}]", value=roles_str, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botinfo", description="Display technical statistics and uptime about this bot.")
    async def botinfo(self, interaction: discord.Interaction):
        uptime_seconds = int(time.time() - self.start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        total_guilds = len(self.bot.guilds)
        total_users = sum(g.member_count or 0 for g in self.bot.guilds)

        embed = discord.Embed(
            title=f"{self.bot.user.name} Information",
            color=discord.Color.teal(),
        )
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.add_field(name="⏱️ Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="🌐 Servers", value=f"`{total_guilds}`", inline=True)
        embed.add_field(name="👥 Total Reach", value=f"`{total_users} members`", inline=True)
        embed.add_field(name="🐍 Python Version", value=f"`{platform.python_version()}`", inline=True)
        embed.add_field(name="📦 discord.py", value=f"`v{discord.__version__}`", inline=True)
        embed.add_field(name="💻 Platform", value=f"`{platform.system()} {platform.release()}`", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="List all available slash commands.")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Bot Command Help Directory",
            description="Here is a list of all commands available on this bot:",
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="🛠️ Utility",
            value=(
                "`/ping` - Check latency and response time\n"
                "`/serverinfo` - Display server information and member counts\n"
                "`/userinfo [user]` - View account details for yourself or another user\n"
                "`/botinfo` - Show uptime, version stats, and system info\n"
                "`/help` - Display this command directory"
            ),
            inline=False,
        )

        embed.add_field(
            name="🧰 Tools & Productivity",
            value=(
                "`/avatar [user]` - View & get download links for user avatar\n"
                "`/poll <question> <opt1> <opt2> [opt3] [opt4]` - Live interactive button poll\n"
                "`/remind <time> <reminder>` - Set a timed reminder (e.g. `10m`, `1h`)\n"
                "`/calc <expression>` - Safe math calculator (`2+2`, `10*5`, `2**8`)"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎲 Fun & Games",
            value=(
                "`/rps` - Play Rock Paper Scissors with clickable buttons\n"
                "`/roll [dice]` - Roll dice (e.g., `1d6`, `2d20`, `1d100`)\n"
                "`/coinflip` - Flip a coin (Heads or Tails)\n"
                "`/8ball <question>` - Ask the Magic 8-Ball for an answer\n"
                "`/joke [category]` - Funny joke (Programming, Dad Jokes, Gaming, General)\n"
                "`/choose <options>` - Pick randomly between choices (`Pizza, Tacos, Burgers`)"
            ),
            inline=False,
        )

        embed.add_field(
            name="🛡️ Moderation (Requires Permissions)",
            value=(
                "`/timeout <member> <duration> [reason]` - Timeout member (e.g. `10m`, `1h`)\n"
                "`/untimeout <member>` - Remove timeout early\n"
                "`/clear <amount>` - Bulk purge 1-100 messages\n"
                "`/slowmode <seconds>` - Set channel cooldown (0 to disable)\n"
                "`/lock [reason]` & `/unlock` - Lock down or unlock a channel\n"
                "`/kick <user> [reason]` - Kick a member with hierarchy check\n"
                "`/ban <user> [reason]` - Ban a member with message purge"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎫 Support Ticket System",
            value=(
                "`/ticket-panel [channel] [title]` - Deploy interactive Create Ticket panel\n"
                "`/ticket-close [reason]` - Close and delete the active ticket channel\n"
                "`/ticket-add <member>` - Add a user to the active ticket channel\n"
                "`/ticket-remove <member>` - Remove a user from the ticket channel"
            ),
            inline=False,
        )

        embed.set_footer(text="Type / to see Discord's built-in command auto-complete.")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
