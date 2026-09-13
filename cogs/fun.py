import random
import re
import discord
from discord import app_commands
from discord.ext import commands

MAGIC_8BALL_RESPONSES = [
    "🟢 It is certain.",
    "🟢 It is decidedly so.",
    "🟢 Without a doubt.",
    "🟢 Yes definitely.",
    "🟢 You may rely on it.",
    "🟢 As I see it, yes.",
    "🟢 Most likely.",
    "🟢 Outlook good.",
    "🟢 Yes.",
    "🟢 Signs point to yes.",
    "🟡 Reply hazy, try again.",
    "🟡 Ask again later.",
    "🟡 Better not tell you now.",
    "🟡 Cannot predict now.",
    "🟡 Concentrate and ask again.",
    "🔴 Don't count on it.",
    "🔴 My reply is no.",
    "🔴 My sources say no.",
    "🔴 Outlook not so good.",
    "🔴 Very doubtful.",
]

JOKES_BY_CATEGORY = {
    "programming": [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "Why do Java programmers have to wear glasses? Because they don't C#.",
        "There are 10 types of people in the world: those who understand binary, and those who don't.",
        "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
        "How do you comfort a JavaScript bug? You console it.",
        "Why was the JavaScript developer sad? Because they didn't Node how to Express themselves.",
        "Real programmers count from 0.",
        "Why did the developer go broke? Because they used up all their cache.",
        "What's the best thing about a boolean? Even if you are wrong, you are only off by a bit.",
        "An optimist says 'the glass is half full.' A pessimist says 'the glass is half empty.' A programmer says 'the glass is twice as large as necessary.'",
        "There are 2 hard problems in computer science: cache invalidation, naming things, and off-by-one errors.",
        "Hardware is the part of a computer you can kick; software is the part you can only curse at.",
        "Why do Python programmers have low self-esteem? Because they're constantly comparing self to others.",
        "!false — it's funny because it's true.",
        "A programmer's wife asks him: 'Go to the store and buy a loaf of bread. If they have eggs, buy a dozen.' He comes home with 12 loaves of bread.",
        "Why did the functions stop calling each other? Because they had too many arguments.",
    ],
    "dad": [
        "I'm reading a book about anti-gravity. I just can't put it down!",
        "Why don't skeletons fight each other? They don't have the guts.",
        "What do you call fake spaghetti? An impasta!",
        "Why did the scarecrow win an award? Because he was outstanding in his field.",
        "What do you call a factory that makes good products? A satisfactory.",
        "I told my doctor that I broke my arm in two places. He told me to stop going to those places.",
        "Why can't a bicycle stand up on its own? Because it's two-tired.",
        "What did one wall say to the other wall? 'I'll meet you at the corner!'",
        "How does a penguin build its house? Igloos it together.",
        "Why did the math book look so sad? Because it had too many problems.",
        "What do you call a sleeping dinosaur? A dino-snore.",
        "Why don't eggs tell jokes? They'd crack each other up.",
        "Did you hear about the guy who invented the knock-knock joke? He won the 'no-bell' prize.",
        "What do you call cheese that isn't yours? Nacho cheese.",
        "I used to play piano by ear, but now I use my hands.",
        "What do you call a belt made of watches? A waist of time.",
    ],
    "gaming": [
        "Why did the creeper cross the road? To blow up the chicken on the other side.",
        "Why is Ghost in Call of Duty so good at hide-and-seek? Because he stays off the radar.",
        "What is a Minecraft player's favorite sport? Boxing.",
        "Why did Mario break up with Princess Peach? She was always in another castle.",
        "Why don't gamers get sunburned? Because they avoid outside at all costs.",
        "Why did Sonic open a bakery? Because he makes fast rolls.",
        "What does a gaming PC have in common with an air conditioner? Both keep the room cool... until you launch Cyberpunk.",
        "How does Link celebrate his birthday? With a hearty meal and lots of pots smashed.",
        "Why did Pac-Man fail his driving test? He kept turning sharp corners and eating dots.",
        "What do you call an AFK sniper in CS:GO? Target practice.",
        "Why was the Nintendo Switch feeling down? It had joy-con drift.",
        "Why do Skyrim guards hate adventuring? An arrow to the knee.",
    ],
    "general": [
        "I told my computer I needed a break, and now it won't stop sending me Kit-Kats.",
        "I asked the librarian if the library had books about paranoia. She whispered: 'They're right behind you...'",
        "Parallel lines have so much in common. It's a shame they'll never meet.",
        "I'm on a seafood diet. I see food and I eat it.",
        "My wife told me to stop impersonating a flamingo. I had to put my foot down.",
        "What did the zero say to the eight? Nice belt!",
        "I would tell a chemistry joke, but I know I wouldn't get a reaction.",
        "Why did the coffee file a police report? It got mugged.",
        "I'm writing a paper on reverse psychology. Please don't read it.",
        "Time flies like an arrow. Fruit flies like a banana.",
        "I invented a new word today! Plagiarism.",
        "Never trust atoms. They make up everything.",
    ],
}

ALL_JOKES = [joke for jokes in JOKES_BY_CATEGORY.values() for joke in jokes]

class RPSView(discord.ui.View):
    def __init__(self, author: discord.User | discord.Member):
        super().__init__(timeout=45.0)
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ This game is not for you! Start your own with `/rps`.", ephemeral=True)
            return False
        return True

    def evaluate(self, player: str, bot_choice: str) -> tuple[str, discord.Color]:
        if player == bot_choice:
            return "🤝 It's a Tie!", discord.Color.gold()

        wins = {
            "Rock": "Scissors",
            "Paper": "Rock",
            "Scissors": "Paper",
        }

        if wins[player] == bot_choice:
            return "🎉 You Won!", discord.Color.green()
        else:
            return "💀 You Lost!", discord.Color.red()

    async def process_choice(self, interaction: discord.Interaction, player_choice: str):
        bot_choice = random.choice(["Rock", "Paper", "Scissors"])
        outcome, color = self.evaluate(player_choice, bot_choice)

        emojis = {"Rock": "🪨", "Paper": "📄", "Scissors": "✂️"}

        embed = discord.Embed(
            title=f"Rock Paper Scissors - {outcome}",
            color=color,
        )
        embed.add_field(name="Your Choice", value=f"{emojis[player_choice]} {player_choice}", inline=True)
        embed.add_field(name="Bot's Choice", value=f"{emojis[bot_choice]} {bot_choice}", inline=True)
        embed.set_footer(text=f"Played by {interaction.user.display_name}")

        # Disable all buttons after choice
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.primary, emoji="🪨")
    async def rock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "Rock")

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.success, emoji="📄")
    async def paper_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "Paper")

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.danger, emoji="✂️")
    async def scissors_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "Scissors")

class FunCog(commands.Cog, name="Fun"):
    """Casual games, interactive mini-games, and entertaining commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors with interactive buttons!")
    async def rps(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎮 Rock Paper Scissors",
            description="Click a button below to make your move!",
            color=discord.Color.blurple(),
        )
        view = RPSView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="coinflip", description="Flip a coin!")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙"

        embed = discord.Embed(
            title=f"{emoji} Coin Flip",
            description=f"{interaction.user.mention} flipped a coin and got **{result}**!",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roll", description="Roll one or more dice (e.g. 1d6, 2d20, d100).")
    @app_commands.describe(dice="Dice notation in the format [count]d[sides] (default: 1d6)")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
        dice_pattern = re.compile(r"^(\d+)?d(\d+)$", re.IGNORECASE)
        match = dice_pattern.match(dice.strip())

        if not match:
            await interaction.response.send_message(
                "❌ Invalid format! Please use dice notation like `1d6`, `2d20`, `d100`, or `3d8`.",
                ephemeral=True,
            )
            return

        count = int(match.group(1)) if match.group(1) else 1
        sides = int(match.group(2))

        if count < 1 or count > 50:
            await interaction.response.send_message("❌ Dice count must be between 1 and 50.", ephemeral=True)
            return

        if sides < 2 or sides > 1000:
            await interaction.response.send_message("❌ Dice sides must be between 2 and 1000.", ephemeral=True)
            return

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)

        embed = discord.Embed(
            title="🎲 Dice Roll",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Input", value=f"`{count}d{sides}`", inline=True)
        embed.add_field(name="Total", value=f"**{total}**", inline=True)

        rolls_str = ", ".join(map(str, rolls))
        if len(rolls_str) > 1000:
            rolls_str = rolls_str[:1000] + "..."
        embed.add_field(name="Rolls", value=f"[{rolls_str}]", inline=False)
        embed.set_footer(text=f"Rolled by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8ball", description="Ask the Magic 8-Ball any question.")
    @app_commands.describe(question="The question you want to ask")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        answer = random.choice(MAGIC_8BALL_RESPONSES)

        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.dark_magenta(),
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)
        embed.set_footer(text=f"Asked by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="joke", description="Get a funny joke! Pick a category or get a random one.")
    @app_commands.describe(category="Optional joke category")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Any / Random", value="any"),
            app_commands.Choice(name="Programming & Tech", value="programming"),
            app_commands.Choice(name="Dad Jokes & Puns", value="dad"),
            app_commands.Choice(name="Gaming", value="gaming"),
            app_commands.Choice(name="General & Witty", value="general"),
        ]
    )
    async def joke(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
    ):
        cat_key = category.value if category else "any"
        if cat_key == "any" or cat_key not in JOKES_BY_CATEGORY:
            selected_joke = random.choice(ALL_JOKES)
            cat_display = "Random"
        else:
            selected_joke = random.choice(JOKES_BY_CATEGORY[cat_key])
            cat_display = category.name

        embed = discord.Embed(
            title=f"😄 Joke • {cat_display}",
            description=selected_joke,
            color=discord.Color.random(),
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="choose", description="Randomly pick between multiple options.")
    @app_commands.describe(options="Separate your choices with commas (e.g. Pizza, Burgers, Tacos)")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [c.strip() for c in options.split(",") if c.strip()]
        if len(choices) < 2:
            await interaction.response.send_message("❌ Please provide at least 2 comma-separated options!", ephemeral=True)
            return

        picked = random.choice(choices)
        embed = discord.Embed(
            title="🎯 Choice Picker",
            description=f"Out of **{len(choices)}** choices, I picked:\n\n✨ **{picked}** ✨",
            color=discord.Color.teal(),
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(FunCog(bot))
