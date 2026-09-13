import asyncio
import re
import discord
from discord import app_commands
from discord.ext import commands

def sanitize_channel_name(name: str) -> str:
    """Sanitize username into a valid Discord text-channel name."""
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", name.lower().replace(" ", "-"))
    return clean[:25] or "user"

class TicketConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60.0)

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(view=self)

        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Ticket closed by {interaction.user.mention}.\nThis channel will be deleted in **5 seconds**...",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(content="Ticket closure cancelled.", view=self)

class TicketControlView(discord.ui.View):
    """Persistent controls placed inside every created ticket channel."""

    def __init__(self, bot: commands.Bot | None = None):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="custom_bot_ticket_close_btn",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Close Ticket Confirmation",
            description="Are you sure you want to close and delete this ticket channel?",
            color=discord.Color.orange(),
        )
        view = TicketConfirmCloseView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(
        label="Claim Ticket",
        style=discord.ButtonStyle.secondary,
        emoji="🙋",
        custom_id="custom_bot_ticket_claim_btn",
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
            return

        # Check if user has moderate/manage permissions
        if not interaction.user.guild_permissions.manage_channels and not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ Only staff/moderators can claim tickets.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Ticket Claimed",
            description=f"This ticket is now being handled by {interaction.user.mention}.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed)

class TicketLauncherView(discord.ui.View):
    """Persistent panel button for members to open tickets."""

    def __init__(self, bot: commands.Bot | None = None):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="custom_bot_ticket_launcher_btn",
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if not guild:
            return

        # Ensure bot has permission to manage channels
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ I lack the `Manage Channels` permission to create ticket channels.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        user_tag = f"ticket-{sanitize_channel_name(interaction.user.name)}"
        topic_identifier = f"Ticket Owner ID: {interaction.user.id}"

        # Check if user already has an active ticket channel
        for channel in guild.text_channels:
            if channel.topic and topic_identifier in channel.topic:
                await interaction.followup.send(
                    f"⚠️ You already have an open ticket in {channel.mention}!",
                    ephemeral=True,
                )
                return

        # Find or create a 'Tickets' category
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            try:
                category = await guild.create_category("Tickets", reason="Category for support tickets")
            except discord.HTTPException:
                category = None

        # Build channel permission overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }

        # Create ticket channel
        try:
            ticket_channel = await guild.create_text_channel(
                name=user_tag,
                category=category,
                overwrites=overwrites,
                topic=f"{topic_identifier} | Opened by {interaction.user.name}",
                reason=f"Support ticket created by {interaction.user.name}",
            )
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Failed to create ticket channel: {e}", ephemeral=True)
            return

        # Send welcome message inside the new ticket channel
        ticket_embed = discord.Embed(
            title=f"Support Ticket - {interaction.user.display_name}",
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                "Please describe your issue or question in detail. A staff member will be with you shortly.\n\n"
                "• Use the buttons below to **Close** or **Claim** this ticket.\n"
                "• Staff can add members with `/ticket-add`."
            ),
            color=discord.Color.brand_green(),
        )
        ticket_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        ticket_embed.set_footer(text="Support Team • Click Close when resolved")

        control_view = TicketControlView(self.bot)
        await ticket_channel.send(content=f"{interaction.user.mention} Support is ready!", embed=ticket_embed, view=control_view)

        await interaction.followup.send(
            f"✅ Your ticket has been created in {ticket_channel.mention}!",
            ephemeral=True,
        )

class TicketsCog(commands.Cog, name="Tickets"):
    """Comprehensive support ticket system with interactive buttons and persistent state."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticket-panel", description="Deploy the interactive ticket creation panel.")
    @app_commands.describe(
        channel="Channel to send the panel to (defaults to current channel)",
        title="Custom title for the panel embed",
        description="Custom description instructions for the panel",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        title: str = "🎫 Support & Help Desk",
        description: str = "Need assistance, have questions, or want to report an issue?\nClick the **Create Ticket** button below to open a private ticket with our team.",
    ):
        target_channel = channel or interaction.channel
        if not target_channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message("❌ I do not have permission to send messages in that channel.", ephemeral=True)
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="A private channel will be automatically created for you.")
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        launcher_view = TicketLauncherView(self.bot)
        await target_channel.send(embed=embed, view=launcher_view)

        await interaction.response.send_message(
            f"✅ Ticket panel successfully deployed to {target_channel.mention}!",
            ephemeral=True,
        )

    @app_commands.command(name="ticket-close", description="Close and delete the current ticket channel.")
    @app_commands.describe(reason="Reason for closing the ticket (optional)")
    @app_commands.guild_only()
    async def ticket_close(self, interaction: discord.Interaction, reason: str | None = None):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Close Ticket Confirmation",
            description="Are you sure you want to close and delete this ticket channel?" + (f"\n**Reason:** {reason}" if reason else ""),
            color=discord.Color.orange(),
        )
        view = TicketConfirmCloseView()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="ticket-add", description="Add a member to this ticket channel.")
    @app_commands.describe(member="Member to add to this ticket")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def ticket_add(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
            return

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        )
        embed = discord.Embed(
            title="Member Added",
            description=f"👤 {member.mention} has been added to this ticket by {interaction.user.mention}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ticket-remove", description="Remove a member from this ticket channel.")
    @app_commands.describe(member="Member to remove from this ticket")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def ticket_remove(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot remove yourself from the ticket. Use `/ticket-close` instead.", ephemeral=True)
            return

        await interaction.channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(
            title="Member Removed",
            description=f"🚫 {member.mention} has been removed from this ticket by {interaction.user.mention}.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    # Register persistent views so buttons continue working after bot restarts
    bot.add_view(TicketLauncherView(bot))
    bot.add_view(TicketControlView(bot))
    await bot.add_cog(TicketsCog(bot))
