import random
import discord
from discord import app_commands
from discord.ext import commands

TRIVIA_QUESTIONS = [
    {
        "question": "Which planet is known as the Red Planet?",
        "options": ["Venus", "Mars", "Jupiter", "Saturn"],
        "correct": 1,
        "explanation": "Mars appears reddish because of the iron oxide (rust) on its surface.",
    },
    {
        "question": "What is the powerhouse of the cell?",
        "options": ["Nucleus", "Ribosome", "Mitochondria", "Endoplasmic Reticulum"],
        "correct": 2,
        "explanation": "Mitochondria generate most of the chemical energy needed to power the cell's biochemical reactions.",
    },
    {
        "question": "In what year was the first iPhone released?",
        "options": ["2005", "2007", "2008", "2010"],
        "correct": 1,
        "explanation": "Steve Jobs introduced the first iPhone on January 9, 2007.",
    },
    {
        "question": "What does CPU stand for?",
        "options": ["Central Processing Unit", "Computer Personal Unit", "Central Program Utility", "Core Processor Unity"],
        "correct": 0,
        "explanation": "CPU stands for Central Processing Unit.",
    },
    {
        "question": "Which programming language was created by Guido van Rossum?",
        "options": ["Ruby", "Python", "Java", "C++"],
        "correct": 1,
        "explanation": "Guido van Rossum released Python in 1991.",
    },
    {
        "question": "How many hearts does an octopus have?",
        "options": ["1", "2", "3", "4"],
        "correct": 2,
        "explanation": "An octopus has three hearts: two pump blood to the gills, while a third pumps blood to the rest of the body.",
    },
    {
        "question": "Which video game franchise features the character 'Master Chief'?",
        "options": ["Gears of War", "Halo", "Destiny", "Doom"],
        "correct": 1,
        "explanation": "Master Chief is the iconic protagonist of Microsoft's Halo series.",
    },
    {
        "question": "What is the chemical symbol for Gold?",
        "options": ["Ag", "Fe", "Au", "Pb"],
        "correct": 2,
        "explanation": "Au comes from the Latin word for gold, 'aurum'.",
    },
    {
        "question": "What is the fastest land animal in the world?",
        "options": ["Cheetah", "Pronghorn", "Lion", "Falcon"],
        "correct": 0,
        "explanation": "The cheetah can reach speeds up to 70 mph (112 km/h).",
    },
    {
        "question": "Which game won Game of the Year at The Game Awards in 2022?",
        "options": ["God of War Ragnarok", "Elden Ring", "Horizon Forbidden West", "Stray"],
        "correct": 1,
        "explanation": "FromSoftware's Elden Ring won Game of the Year in 2022.",
    },
]

class TriviaView(discord.ui.View):
    def __init__(self, author: discord.User | discord.Member, trivia: dict):
        super().__init__(timeout=30.0)
        self.author = author
        self.trivia = trivia
        self.answered = False

        emojis = ["🇦", "🇧", "🇨", "🇩"]
        for idx, option_text in enumerate(trivia["options"]):
            btn = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label=option_text,
                emoji=emojis[idx],
                custom_id=f"trivia_opt_{idx}",
            )
            btn.callback = self.make_callback(idx)
            self.add_item(btn)

    def make_callback(self, chosen_idx: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author.id:
                await interaction.response.send_message("❌ Start your own trivia round using `/trivia`!", ephemeral=True)
                return

            if self.answered:
                return
            self.answered = True

            correct_idx = self.trivia["correct"]
            is_correct = chosen_idx == correct_idx

            for idx, child in enumerate(self.children):
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
                    if idx == correct_idx:
                        child.style = discord.ButtonStyle.success
                    elif idx == chosen_idx and not is_correct:
                        child.style = discord.ButtonStyle.danger

            if is_correct:
                embed_color = discord.Color.green()
                title = "🎉 Correct Answer!"
            else:
                embed_color = discord.Color.red()
                title = "❌ Incorrect!"

            embed = discord.Embed(
                title=title,
                description=(
                    f"**Question:** {self.trivia['question']}\n\n"
                    f"**Correct Answer:** {self.trivia['options'][correct_idx]}\n"
                    f"💡 *{self.trivia['explanation']}*"
                ),
                color=embed_color,
            )
            embed.set_footer(text=f"Played by {interaction.user.display_name}")

            await interaction.response.edit_message(embed=embed, view=self)

        return callback

class GamesCog(commands.Cog, name="Games"):
    """Fun mini-games, social actions, and community entertainment."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="trivia", description="Play a multiple-choice trivia question with clickable buttons!")
    async def trivia(self, interaction: discord.Interaction):
        item = random.choice(TRIVIA_QUESTIONS)
        embed = discord.Embed(
            title="🧠 Trivia Time!",
            description=f"**{item['question']}**\n\nChoose the correct option below:",
            color=discord.Color.purple(),
        )
        embed.set_footer(text=f"Time limit: 30 seconds • Requested by {interaction.user.display_name}")

        view = TriviaView(interaction.user, item)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="ship", description="Calculate the love & compatibility percentage between two users!")
    @app_commands.describe(user1="First user", user2="Second user (defaults to you)")
    async def ship(self, interaction: discord.Interaction, user1: discord.User, user2: discord.User | None = None):
        target2 = user2 or interaction.user
        if user1.id == target2.id:
            await interaction.response.send_message("❤️ Self-love is the best love! (100%)", ephemeral=True)
            return

        # Seed compatibility deterministically based on user IDs
        seed_val = (user1.id * target2.id) % 101
        percentage = seed_val

        # Create visual progress bar (10 blocks)
        filled = round(percentage / 10)
        empty = 10 - filled
        progress_bar = "🟩" * filled + "⬛" * empty

        if percentage >= 90:
            verdict = "💍 Soulmates! When's the wedding?"
            color = discord.Color.fuchsia()
        elif percentage >= 70:
            verdict = "💖 Highly compatible! Sparks are flying!"
            color = discord.Color.pink()
        elif percentage >= 50:
            verdict = "💛 Good chemistry with great potential."
            color = discord.Color.gold()
        elif percentage >= 30:
            verdict = "🤝 Better off as good friends."
            color = discord.Color.orange()
        else:
            verdict = "💔 Absolute disaster. Run away!"
            color = discord.Color.red()

        embed = discord.Embed(
            title="💘 Love Compatibility Meter",
            description=f"**{user1.display_name}** + **{target2.display_name}**",
            color=color,
        )
        embed.add_field(name="Compatibility", value=f"**{percentage}%**\n`{progress_bar}`", inline=False)
        embed.add_field(name="Verdict", value=verdict, inline=False)
        embed.set_footer(text="Love Calculator • 100% scientifically accurate")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hug", description="Give another member a warm hug.")
    @app_commands.describe(member="The member to hug")
    @app_commands.guild_only()
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        if member.id == interaction.user.id:
            msg = f"{interaction.user.mention} wraps their arms around themselves for a cozy self-hug. 🤗"
        else:
            msg = f"🤗 {interaction.user.mention} gives {member.mention} a warm, supportive hug!"

        embed = discord.Embed(description=msg, color=discord.Color.pink())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slap", description="Playfully slap another member with a fish.")
    @app_commands.describe(member="The member to slap")
    @app_commands.guild_only()
    async def slap(self, interaction: discord.Interaction, member: discord.Member):
        if member.id == interaction.user.id:
            await interaction.response.send_message("Why would you slap yourself? Be kind to yourself!", ephemeral=True)
            return

        embed = discord.Embed(
            description=f"🐟 {interaction.user.mention} slaps {member.mention} with a large, smelly trout!",
            color=discord.Color.dark_orange(),
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(GamesCog(bot))
