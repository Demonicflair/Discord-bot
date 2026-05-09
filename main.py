import discord
from discord.ext import commands
import asyncio
import os
import time
import traceback
import sqlite3

# Import your other files
import config
import database 

# =========================
# DYNAMIC PREFIX
# =========================
prefix_db = sqlite3.connect("prefixes.db", check_same_thread=False)
prefix_cursor = prefix_db.cursor()
prefix_cursor.execute("CREATE TABLE IF NOT EXISTS prefixes(guild_id INTEGER PRIMARY KEY, prefix TEXT)")
prefix_db.commit()

def get_prefix(bot, message):
    if not message.guild:
        return "!"
    prefix_cursor.execute("SELECT prefix FROM prefixes WHERE guild_id=?", (message.guild.id,))
    data = prefix_cursor.fetchone()
    return data[0] if data else "!"

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

startup_time = time.time()

# =========================
# LOAD COGS
# =========================
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Loaded: {filename}")
            except Exception as e:
                print(f"❌ Failed {filename}: {e}")

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    # Initialize the database correctly
    try:
        await database.initialize_db()
        print("🗄️ Database Ready")
    except Exception as e:
        print(f"⚠️ DB Init Error: {e}")

    # Sync Slash Commands
    try:
        await bot.tree.sync()
        print(f"✅ Slash Commands Synced")
    except Exception as e:
        print(f"⚠️ Sync Error: {e}")

    print(f"🤖 Connected as: {bot.user}")

# =========================
# RUN BOT
# =========================
async def main():
    async with bot:
        await load_cogs()
        # Make sure TOKEN is exactly as it is in Railway variables
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
