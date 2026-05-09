import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import sys
import aiosqlite

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
import database 
# Import the views from your cogs to register them
from cogs.tickets import TicketView, TicketControlView
from cogs.antinuke import ModPanel

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.all() 

class EliteBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix_async,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def get_prefix_async(self, bot, message):
        """Async prefix fetcher to prevent bot lag."""
        if not message.guild:
            return "!"
        try:
            async with aiosqlite.connect("bot.db") as db:
                async with db.execute("SELECT prefix FROM prefixes WHERE guild_id=?", (message.guild.id,)) as cursor:
                    res = await cursor.fetchone()
                    return res[0] if res else "!"
        except:
            return "!"

    async def setup_hook(self):
        # 1. Register Persistent Views (The "Famous Bot" Secret)
        # This makes buttons work after a restart!
        self.add_view(TicketView())
        self.add_view(TicketControlView())
        # Note: ModPanel usually doesn't need global registration as it's short-term, 
        # but TicketView absolutely does.

        # 2. Loading Cogs
        print("🚀 Loading Cogs...")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ {filename} loaded.")
                except Exception as e:
                    print(f"❌ {filename} failed: {e}")
        
        # 3. Syncing Slash Commands
        await self.tree.sync()
        print("🔗 Slash Commands Synced Globaly.")

bot = EliteBot()

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    await database.initialize_db()
    
    # Custom Activity Status
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"over {len(bot.guilds)} servers | !")
    await bot.change_presence(status=discord.Status.online, activity=activity)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🛡️  {bot.user.name} is now PROTECTING {len(bot.guilds)} servers")
    print(f"📡  Latency: {round(bot.latency * 1000)}ms")
    print(f"🛠️  Persistent Views: Registered")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# =========================
# RUNNING THE BOT
# =========================
async def start_bot():
    async with bot:
        try:
            await bot.start(config.TOKEN)
        except discord.LoginFailure:
            print("❌ ERROR: Invalid Token!")

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("📴 Bot is shutting down...")
