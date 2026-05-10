import discord
from discord.ext import commands
import os
import asyncio
from config import TOKEN, PREFIX
from utils.database import initialize_db

# Import Persistent Views from your cogs to register them
# This keeps buttons working after the bot restarts!
from cogs.tickets import TicketControlView, TicketView

class DemBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or(PREFIX),
            intents=intents,
            help_command=None # Using your custom help.py instead
        )

    async def setup_hook(self):
        # 1. Initialize Database
        await initialize_db()
        print("📁 Database Tables Verified.")

        # 2. Register Persistent Views
        self.add_view(TicketControlView())
        self.add_view(TicketView())
        print("🔘 Persistent Views Registered.")

        # 3. Load Cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"✅ Loaded: {filename}")
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")

    async def on_ready(self):
        print(f"🚀 {self.user} is online and protecting {len(self.guilds)} servers.")
        await self.tree.sync()
        print("🔄 Slash Commands Synchronized.")

bot = DemBot()

if __name__ == "__main__":
    bot.run(TOKEN)
