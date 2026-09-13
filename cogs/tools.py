import ast
import asyncio
import operator
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

# Safe AST math evaluator
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Unsupported constant type")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            left = safe_eval(node.left)
            right = safe_eval(node.right)
            # Guard against huge power calculations
            if op_type == ast.Pow and (right > 100 or left > 10000):
                raise ValueError("Exponent too large")
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported operator {op_type}")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](safe_eval(node.operand))
        raise ValueError(f"Unsupported unary operator {op_type}")
    else:
        raise ValueError("Invalid mathematical expression")

class PollButton(discord.ui.Button):
    def __init__(self, option_index: int, label: str, emoji: str):
        super().__init__(style=discord.ButtonStyle.secondary, label=f"{label} (0)", emoji=emoji)
        self.option_index = option_index
        self.clean_label = label

    async def callback(self, interaction: discord.Interaction):
        view: PollView = self.view
        user_id = interaction.user.id

        # Check if user already voted for this exact option
        if user_id in view.votes[self.option_index]:
            view.votes[self.option_index].remove(user_id)
            action_text = "removed your vote from"
        else:
            # Remove vote from any previous option (single-vote poll)
            for idx in view.votes:
                if user_id in view.votes[idx]:
                    view.votes[idx].remove(user_id)
            view.votes[self.option_index].add(user_id)
            action_text = "voted for"

        # Update button labels with new counts
        for child in view.children:
            if isinstance(child, PollButton):
                count = len(view.votes[child.option_index])
                child.label = f"{child.clean_label} ({count})"

        # Update embed description with totals
        total_votes = sum(len(v) for v in view.votes.values())
        view.embed.set_footer(text=f"Total Votes: {total_votes} • Poll created by {view.author.display_name}")

        await interaction.response.edit_message(embed=view.embed, view=view)
        await interaction.followup.send(f"You {action_text} **{self.clean_label}**.", ephemeral=True)

class PollView(discord.ui.View):
    def __init__(self, author: discord.User | discord.Member, embed: discord.Embed, options: list[str]):
        super().__init__(timeout=None)  # Persistent view
        self.author = author
        self.embed = embed
        self.votes: dict[int, set[int]] = {i: set() for i in range(len(options))}

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        for i, opt in enumerate(options):
            self.add_item(PollButton(option_index=i, label=opt[:50], emoji=emojis[i]))

class ToolsCog(commands.Cog, name="Tools"):
    """Productivity and interactive utility tools."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="View and get direct download links for a user's avatar.")
    @app_commands.describe(user="User whose avatar to display (defaults to you)")
    async def avatar(self, interaction: discord.Interaction, user: discord.User | None = None):
        target = user or interaction.user
        avatar = target.display_avatar

        embed = discord.Embed(
            title=f"Avatar of {target.display_name}",
            color=discord.Color.blurple(),
        )
        embed.set_image(url=avatar.url)
        embed.description = (
            f"[**PNG**]({avatar.with_format('png').url}) | "
            f"[**JPG**]({avatar.with_format('jpg').url}) | "
            f"[**WEBP**]({avatar.with_format('webp').url})"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create an interactive poll with live voting buttons.")
    @app_commands.describe(
        question="What are you polling about?",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
    )
    @app_commands.guild_only()
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str | None = None,
        option4: str | None = None,
    ):
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)

        embed = discord.Embed(
            title=f"📊 {question}",
            description="Click a button below to cast or change your vote!",
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Total Votes: 0 • Poll created by {interaction.user.display_name}")

        view = PollView(author=interaction.user, embed=embed, options=options)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="remind", description="Set a timed reminder for yourself.")
    @app_commands.describe(
        time="Time delay format: e.g. 30s, 10m, 2h, 1d",
        reminder="What should I remind you about?",
    )
    async def remind(self, interaction: discord.Interaction, time: str, reminder: str):
        seconds = parse_time(time)
        if not seconds or seconds < 5:
            await interaction.response.send_message("❌ Invalid duration! Minimum 5s (e.g., `30s`, `15m`, `1h`).", ephemeral=True)
            return

        if seconds > 86400 * 7:
            await interaction.response.send_message("❌ Maximum reminder duration is 7 days.", ephemeral=True)
            return

        target_time = discord.utils.utcnow() + timedelta(seconds=seconds)
        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=f"I will remind you about **{reminder}** {discord.utils.format_dt(target_time, style='R')}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Non-blocking async sleep
        await asyncio.sleep(seconds)

        # Trigger reminder
        reminder_embed = discord.Embed(
            title="⏰ Reminder Alert!",
            description=f"Hey {interaction.user.mention}, you asked to be reminded about:\n\n**{reminder}**",
            color=discord.Color.gold(),
        )
        try:
            if interaction.channel:
                await interaction.channel.send(content=interaction.user.mention, embed=reminder_embed)
            else:
                await interaction.user.send(embed=reminder_embed)
        except discord.HTTPException:
            pass

    @app_commands.command(name="calc", description="Safely evaluate a mathematical expression.")
    @app_commands.describe(expression="Math expression (e.g. 2 + 2, (15 * 3) / 2, 2**8)")
    async def calc(self, interaction: discord.Interaction, expression: str):
        try:
            parsed = ast.parse(expression.strip(), mode="eval")
            result = safe_eval(parsed)

            if isinstance(result, float) and result.is_integer():
                result = int(result)

            embed = discord.Embed(
                title="🧮 Calculator",
                color=discord.Color.dark_teal(),
            )
            embed.add_field(name="Expression", value=f"`{expression}`", inline=False)
            embed.add_field(name="Result", value=f"**{result}**", inline=False)
            await interaction.response.send_message(embed=embed)
        except Exception:
            await interaction.response.send_message(
                "❌ Invalid or unsupported expression. Supported operators: `+`, `-`, `*`, `/`, `//`, `%`, `**`.",
                ephemeral=True,
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(ToolsCog(bot))
