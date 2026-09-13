import json
import random
import time
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands

DATA_DIR = Path(__file__).parent.parent / "data"
ECONOMY_FILE = DATA_DIR / "economy.json"

def load_economy_data() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if not ECONOMY_FILE.exists():
        with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_economy_data(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_user_account(data: dict, user_id: int) -> dict:
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "wallet": 100,  # Starting bonus
            "bank": 0,
            "last_daily": 0,
            "last_beg": 0,
            "streak": 0,
        }
    return data[uid]

SLOT_SYMBOLS = ["🍒", "🍋", "🍇", "🔔", "⭐", "💎", "7️⃣"]

class EconomyCog(commands.Cog, name="Economy"):
    """Server economy system with currency, daily bonuses, gambling, and leaderboards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your or another member's coin balance.")
    @app_commands.describe(user="The member whose balance to check (defaults to you)")
    async def balance(self, interaction: discord.Interaction, user: discord.User | None = None):
        target = user or interaction.user
        data = load_economy_data()
        account = get_user_account(data, target.id)

        wallet = account["wallet"]
        bank = account["bank"]
        net_worth = wallet + bank
        streak = account.get("streak", 0)

        embed = discord.Embed(
            title=f"💳 Economy Account: {target.display_name}",
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🪙 Wallet", value=f"**{wallet:,}** coins", inline=True)
        embed.add_field(name="🏦 Bank", value=f"**{bank:,}** coins", inline=True)
        embed.add_field(name="💰 Net Worth", value=f"**{net_worth:,}** coins", inline=True)
        embed.add_field(name="🔥 Daily Streak", value=f"**{streak}** days", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily coin reward and build your streak!")
    async def daily(self, interaction: discord.Interaction):
        data = load_economy_data()
        account = get_user_account(data, interaction.user.id)

        now = int(time.time())
        cooldown = 86400  # 24 hours
        streak_timeout = 86400 * 2  # 48 hours to preserve streak

        time_since = now - account["last_daily"]
        if time_since < cooldown:
            remaining = cooldown - time_since
            hours, remainder = divmod(remaining, 3600)
            minutes, _ = divmod(remainder, 60)
            await interaction.response.send_message(
                f"⏳ You have already claimed your daily reward! Come back in **{hours}h {minutes}m**.",
                ephemeral=True,
            )
            return

        # Check streak
        if time_since <= streak_timeout:
            account["streak"] = account.get("streak", 0) + 1
        else:
            account["streak"] = 1

        base_reward = 500
        streak_bonus = min(account["streak"] * 50, 1000)
        total_reward = base_reward + streak_bonus

        account["wallet"] += total_reward
        account["last_daily"] = now
        save_economy_data(data)

        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=(
                f"You claimed **+{total_reward:,}** coins!\n"
                f"• Base: `+{base_reward:,}` coins\n"
                f"• Streak Bonus: `+{streak_bonus:,}` coins\n\n"
                f"🔥 Current Streak: **{account['streak']}** days!"
            ),
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Total Balance: {account['wallet']:,} coins")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="beg", description="Beg for spare coins (has a short cooldown).")
    async def beg(self, interaction: discord.Interaction):
        data = load_economy_data()
        account = get_user_account(data, interaction.user.id)

        now = int(time.time())
        cooldown = 45  # 45 seconds

        time_since = now - account.get("last_beg", 0)
        if time_since < cooldown:
            await interaction.response.send_message(
                f"⏳ Take a breather! You can beg again in **{cooldown - time_since}** seconds.",
                ephemeral=True,
            )
            return

        account["last_beg"] = now

        # 80% chance to succeed, 20% chance to get nothing
        if random.random() < 0.20:
            responses = [
                "A pedestrian looked at you with disgust and walked away.",
                "Discord mods banned you from the street corner. You got 0 coins.",
                "A stray cat hissed at you and ran off.",
                "You reached into an empty tip jar. Nothing there!",
            ]
            save_economy_data(data)
            await interaction.response.send_message(f"😢 {random.choice(responses)}", ephemeral=True)
            return

        earned = random.randint(15, 120)
        benefactors = [
            "A generous tech billionaire",
            "A kind stranger passing by",
            "A friendly grandma",
            "A mysterious hooded figure",
            "A helpful Discord admin",
            "A street musician",
        ]
        chosen = random.choice(benefactors)
        account["wallet"] += earned
        save_economy_data(data)

        embed = discord.Embed(
            description=f"🪙 **{chosen}** gave you **+{earned}** coins!",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slots", description="Bet coins on the virtual slot machine!")
    @app_commands.describe(bet="Amount of coins to bet")
    async def slots(self, interaction: discord.Interaction, bet: int):
        if bet <= 0:
            await interaction.response.send_message("❌ Bet must be greater than 0 coins.", ephemeral=True)
            return

        data = load_economy_data()
        account = get_user_account(data, interaction.user.id)

        if account["wallet"] < bet:
            await interaction.response.send_message(
                f"❌ Insufficient funds! You only have **{account['wallet']:,}** coins in your wallet.",
                ephemeral=True,
            )
            return

        account["wallet"] -= bet

        s1 = random.choice(SLOT_SYMBOLS)
        s2 = random.choice(SLOT_SYMBOLS)
        s3 = random.choice(SLOT_SYMBOLS)

        if s1 == s2 == s3:
            multiplier = 5 if s1 != "7️⃣" else 10
            winnings = bet * multiplier
            account["wallet"] += winnings
            result_msg = f"🎉 **JACKPOT!** You won **+{winnings:,}** coins! ({multiplier}x multiplier)"
            color = discord.Color.green()
        elif s1 == s2 or s2 == s3 or s1 == s3:
            multiplier = 2
            winnings = bet * multiplier
            account["wallet"] += winnings
            result_msg = f"✨ **Two matches!** You won **+{winnings:,}** coins! ({multiplier}x)"
            color = discord.Color.gold()
        else:
            winnings = 0
            result_msg = f"💀 You lost **-{bet:,}** coins! Better luck next time."
            color = discord.Color.red()

        save_economy_data(data)

        embed = discord.Embed(
            title="🎰 Virtual Slot Machine",
            description=(
                f"```\n"
                f"╔═════════════╗\n"
                f"║  {s1} │ {s2} │ {s3}  ║\n"
                f"╚═════════════╝\n"
                f"```\n"
                f"{result_msg}\n\n"
                f"🪙 Wallet Balance: **{account['wallet']:,}** coins"
            ),
            color=color,
        )
        embed.set_footer(text=f"Player: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pay", description="Transfer coins from your wallet to another member.")
    @app_commands.describe(recipient="The member to send coins to", amount="Number of coins to transfer")
    @app_commands.guild_only()
    async def pay(self, interaction: discord.Interaction, recipient: discord.Member, amount: int):
        if recipient.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot send coins to yourself!", ephemeral=True)
            return

        if recipient.bot:
            await interaction.response.send_message("❌ You cannot send coins to bots.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be greater than 0 coins.", ephemeral=True)
            return

        data = load_economy_data()
        sender_acc = get_user_account(data, interaction.user.id)
        if sender_acc["wallet"] < amount:
            await interaction.response.send_message(
                f"❌ You don't have enough coins! Your wallet: **{sender_acc['wallet']:,}** coins.",
                ephemeral=True,
            )
            return

        recipient_acc = get_user_account(data, recipient.id)
        sender_acc["wallet"] -= amount
        recipient_acc["wallet"] += amount
        save_economy_data(data)

        embed = discord.Embed(
            title="💸 Payment Successful",
            description=f"**{interaction.user.mention}** transferred **{amount:,}** coins to **{recipient.mention}**!",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the top wealthiest members in the server.")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        data = load_economy_data()
        guild = interaction.guild

        # Collect members present in the guild and calculate net worth
        scores = []
        for uid_str, acc in data.items():
            if uid_str.isdigit():
                member = guild.get_member(int(uid_str))
                if member and not member.bot:
                    net_worth = acc.get("wallet", 0) + acc.get("bank", 0)
                    scores.append((member, net_worth))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_10 = scores[:10]

        if not top_10:
            await interaction.response.send_message("No economy accounts found on this server yet.", ephemeral=True)
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (member, net_worth) in enumerate(top_10):
            rank_icon = medals[i] if i < 3 else f"`#{i+1}`"
            lines.append(f"{rank_icon} **{member.display_name}** — **{net_worth:,}** coins")

        embed = discord.Embed(
            title=f"🏆 Wealth Leaderboard — {guild.name}",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
