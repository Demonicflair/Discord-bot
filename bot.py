import discord
from discord.ext import commands
import os
import asyncio
import config
from utils.logger import init_db

class DemBot(commands.Bot):
    def __init__(self):
        # Intents allow the bot to see members, messages, and events
        intents = discord.Intents.all()
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None, # We use our own custom help cog
            case_insensitive=True
        )

    async def setup_hook(self):
        """This runs before the bot starts connecting to Discord."""
        # 1. Initialize the Database (Creating tables if they don't exist)
        print("🗄️ Initializing SQLite Database...")
        await init_db()

        # 2. Load all Cogs from the /cogs folder
        print("⚙️ Loading modules...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ Module Loaded: {filename}")
                except Exception as e:
                    print(f"❌ Module Failed: {filename} -> {e}")

    async def on_ready(self):
        """This runs when the bot is officially online."""
        print("-" * 30)
        print(f"🚀 {self.user.name} is now ONLINE")
        print(f"🆔 ID: {self.user.id}")
        print(f"🌍 Servers: {len(self.guilds)}")
        print("-" * 30)
        
        # Syncing Slash Commands (This makes them appear in Discord)
        try:
            synced = await self.tree.sync()
            print(f"🪄 Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"⚠️ Failed to sync commands: {e}")

# Create the bot instance
bot = DemBot()

# Start the bot
if __name__ == "__main__":
    bot.run(config.TOKEN)
  
