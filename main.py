import asyncio
import logging
import os
import sys
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Setup clean console logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("DiscordBot")

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")

class CustomBot(commands.Bot):
    def __init__(self):
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,  # We implement a modern slash /help command instead
        )

    async def setup_hook(self):
        """Asynchronously load all cogs from the cogs directory and sync slash commands."""
        cogs_dir = Path(__file__).parent / "cogs"
        if cogs_dir.exists() and cogs_dir.is_dir():
            for file in cogs_dir.glob("*.py"):
                if not file.name.startswith("_"):
                    extension = f"cogs.{file.stem}"
                    try:
                        await self.load_extension(extension)
                        logger.info(f"Loaded extension: {extension}")
                    except Exception as e:
                        logger.error(f"Failed to load extension {extension}: {e}", exc_info=True)

        # Sync slash commands
        try:
            if DEV_GUILD_ID and DEV_GUILD_ID.strip().isdigit():
                guild_id = int(DEV_GUILD_ID.strip())
                guild_obj = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild_obj)
                synced = await self.tree.sync(guild=guild_obj)
                logger.info(f"Synced {len(synced)} slash commands to dev guild ({guild_id}) for instant testing!")
            else:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} slash commands globally (Discord caches this across all servers).")
        except discord.Forbidden as e:
            if e.code == 50001:
                logger.warning(
                    "\n" + "!" * 60 + "\n"
                    "WARNING: Missing Access (Error code 50001) while syncing commands!\n"
                    "This usually means one of the following:\n"
                    "1. The bot is NOT in your server yet (you must invite it to the server first).\n"
                    "2. The bot was invited without the 'applications.commands' scope.\n"
                    "3. DEV_GUILD_ID is incorrect (make sure it's the Server ID, not a channel or user ID).\n\n"
                    "The bot is still running, but slash commands may not be registered yet.\n"
                    "Once the bot is invited with proper scopes, restart the bot to sync.\n"
                    + "!" * 60
                )
            else:
                logger.error(f"Forbidden error while syncing commands: {e}")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}", exc_info=True)

from aiohttp import web

async def start_health_server():
    """Runs a lightweight keep-alive HTTP server for free cloud hosts (Render, Koyeb)."""
    port_str = os.getenv("PORT")
    if not port_str and not os.getenv("KEEP_ALIVE"):
        return  # Skips when running locally without a cloud PORT

    port = int(port_str) if port_str and port_str.isdigit() else 8080
    app = web.Application()

    async def handle_health(request):
        return web.Response(text="Bot is online and running 24/7!", content_type="text/plain")

    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Keep-alive web server active on port {port} (ready for 24/7 ping monitoring)")

async def main():
    if not TOKEN or TOKEN.strip() == "" or TOKEN == "your_bot_token_here":
        logger.error(
            "\n" + "=" * 60 + "\n"
            "ERROR: DISCORD_TOKEN is not configured!\n"
            "Please open the .env file in the project directory and paste your bot token:\n"
            "DISCORD_TOKEN=your_real_token_here\n\n"
            "If you haven't created a bot yet, follow the instructions in the README.\n"
            + "=" * 60
        )
        sys.exit(1)

    bot = CustomBot()
    await start_health_server()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down gracefully.")
