import discord
from discord.ext import commands
import asyncio
import os
import time
import traceback
import sys

# Add current directory to path so Railway finds your files easily
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
import database 

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.all() # Using .all() to ensure no 'Missing Intents' errors on Railway

class EliteBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_dynamic_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def get_dynamic_prefix(self, bot, message):
        if not message.guild:
            return "!"
        try:
            # Reusing your prefix logic but making it safer
            import sqlite3
            conn = sqlite3.connect("prefixes.db")
            cur = conn.cursor()
            cur.execute("SELECT prefix FROM prefixes WHERE guild_id=?", (message.guild.id,))
            res = cur.fetchone()
            conn.close()
            return res[0] if res else "!"
        except:
            return "!"

    async def setup_hook(self):
        # This is the NEW way to load cogs in discord.py 2.0+
        print("🚀 Loading Cogs...")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ {filename} loaded.")
                except Exception as e:
                    print(f"❌ {filename} failed: {e}")
        
        # Syncing Slash Commands
        await self.tree.sync()
        print("🔗 Slash Commands Synced.")

bot = EliteBot()

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    await database.initialize_db()
    
    # Famous Bot Look: Custom Console Banner
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🛡️  {bot.user.name} is now PROTECTING {len(bot.guilds)} servers")
    print(f"📡  Latency: {round(bot.latency * 1000)}ms")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# =========================
# RUNNING THE BOT
# =========================
async def start_bot():
    async with bot:
        try:
            await bot.start(config.TOKEN)
        except discord.LoginFailure:
            print("❌ ERROR: Invalid Token in config.py or Railway Variables!")

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass
