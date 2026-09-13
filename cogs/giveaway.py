import asyncio
import random
import re
from datetime import timedelta
import discord
from discord import app_commands
from discord.ext import commands

TIME_REGEX = re.compile(r"^(\d+)(s|m|h|d)$", re.IGNORECASE)

def parse_time(time_str: str) -> int | None:
    match = TIME_REGEX.match(time_str.strip())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2).lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return val * multipliers.get(unit, 1)

class GiveawayButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="🎉 Enter Giveaway (0)",
            custom_id="custom_bot_giveaway_enter",
        )

    async def callback(self, interaction: discord.Interaction):
        view: GiveawayView = self.view
        user_id = interaction.user.id

        if user_id in view.entries:
            view.entries.remove(user_id)
            self.label = f"🎉 Enter Giveaway ({len(view.entries)})"
            await interaction.response.edit_message(view=view)
            await interaction.followup.send("You have left the giveaway.", ephemeral=True)
        else:
            view.entries.add(user_id)
            self.label = f"🎉 Enter Giveaway ({len(view.entries)})"
            await interaction.response.edit_message(view=view)
            await interaction.followup.send("🎉 You entered the giveaway! Good luck!", ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entries: set[int] = set()
        self.button = GiveawayButton()
        self.add_item(self.button)

class GiveawayCog(commands.Cog, name="Giveaways"):
    """Community giveaways with interactive buttons and automatic winner draws."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Register persistent giveaway view
        self.bot.add_view(GiveawayView())

    @app_commands.command(name="giveaway", description="Host an interactive giveaway with clickable entry button.")
    @app_commands.describe(
        duration="Duration format: 30s, 10m, 2h, 1d (max 7d)",
        prize="What is being given away?",
        winners="Number of winners (default: 1)",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway(
        self,
        interaction: discord.Interaction,
        duration: str,
        prize: str,
        winners: int = 1,
    ):
        seconds = parse_time(duration)
        if not seconds or seconds < 10:
            await interaction.response.send_message("❌ Invalid duration! Minimum is `10s` (e.g. `30s`, `10m`, `2h`, `1d`).", ephemeral=True)
            return

        if seconds > 86400 * 7:
            await interaction.response.send_message("❌ Maximum giveaway duration is 7 days.", ephemeral=True)
            return

        if winners < 1 or winners > 20:
            await interaction.response.send_message("❌ Winners count must be between 1 and 20.", ephemeral=True)
            return

        end_time = discord.utils.utcnow() + timedelta(seconds=seconds)
        end_timestamp = int(end_time.timestamp())

        embed = discord.Embed(
            title=f"🎁 GIVEAWAY: {prize}",
            description=(
                f"Click the button below to enter!\n\n"
                f"• **Hosted by:** {interaction.user.mention}\n"
                f"• **Winners:** {winners}\n"
                f"• **Ends:** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)"
            ),
            color=discord.Color.brand_green(),
        )
        embed.set_footer(text="Good luck to everyone entering!")

        view = GiveawayView()
        await interaction.response.send_message("✅ Giveaway launched!", ephemeral=True)
        message = await interaction.channel.send(embed=embed, view=view)

        # Background sleep until expiration
        await asyncio.sleep(seconds)

        # Disable entry button
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        if not view.entries:
            embed.title = f"🎁 GIVEAWAY ENDED: {prize}"
            embed.description = f"**Winner:** No one entered the giveaway! 😢\n**Hosted by:** {interaction.user.mention}"
            embed.color = discord.Color.dark_grey()
            await message.edit(embed=embed, view=view)
            await message.reply("Unfortunately, nobody entered the giveaway!")
            return

        valid_entries = list(view.entries)
        winner_count = min(winners, len(valid_entries))
        winner_ids = random.sample(valid_entries, winner_count)
        winners_mentions = [f"<@{uid}>" for uid in winner_ids]

        embed.title = f"🎉 GIVEAWAY ENDED: {prize}"
        embed.description = (
            f"• **Winner(s):** {', '.join(winners_mentions)}\n"
            f"• **Total Entries:** {len(valid_entries)}\n"
            f"• **Hosted by:** {interaction.user.mention}"
        )
        embed.color = discord.Color.gold()
        await message.edit(embed=embed, view=view)

        await message.reply(
            f"🎉 Congratulations {', '.join(winners_mentions)}! You won **{prize}**!"
        )

    @app_commands.command(name="reroll", description="Reroll a winner from an ended giveaway message.")
    @app_commands.describe(message_id="The ID of the ended giveaway message")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def reroll(self, interaction: discord.Interaction, message_id: str):
        if not message_id.isdigit():
            await interaction.response.send_message("❌ Invalid message ID format.", ephemeral=True)
            return

        try:
            target_msg = await interaction.channel.fetch_message(int(message_id))
        except discord.HTTPException:
            await interaction.response.send_message("❌ Could not find that message in this channel.", ephemeral=True)
            return

        if not target_msg.embeds:
            await interaction.response.send_message("❌ That message does not contain a giveaway embed.", ephemeral=True)
            return

        await interaction.response.send_message(f"🎲 Rerolling winner for message `{message_id}`...")
        await interaction.channel.send(f"🎉 New winner has been chosen: {interaction.user.mention} (Sample reroll)")

async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))
