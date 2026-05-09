import discord
from discord.ext import commands
import asyncio
import config
import os
import time
import traceback
import sqlite3
import database  # Imported your database file

# =========================
# DYNAMIC PREFIX LOGIC
# =========================
# Note: Keeping this synchronous for now as it's called frequently by the internal API
# but we can async it later if needed.
prefix_db = sqlite3.connect("prefixes.db", check_same_thread=False)
prefix_cursor = prefix_db.cursor()
prefix_cursor.execute("CREATE TABLE IF NOT EXISTS prefixes(guild_id INTEGER PRIMARY KEY, prefix TEXT)")
prefix_db.commit()

DEFAULT_PREFIX = "!"

def get_prefix(bot, message):
    if not message.guild:
        return DEFAULT_PREFIX
    prefix_cursor.execute("SELECT prefix FROM prefixes WHERE guild_id=?", (message.guild.id,))
    data = prefix_cursor.fetchone()
    return data[0] if data else DEFAULT_PREFIX

# =========================
# INTENTS & BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True
intents.presences = True
intents.voice_states = True
intents.emojis_and_stickers = True

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True,
    strip_after_prefix=True
)

startup_time = time.time()

# =========================
# STATUS ROTATION
# =========================
async def status_task():
    await bot.wait_until_ready()
    statuses = [
        "🛡️ Protecting servers",
        "⚡ Ultimate Moderation",
        "🎫 Advanced Ticket System",
        "💣 Anti-Nuke Enabled",
        "📚 /help",
        "🚀 Elite Discord Bot"
    ]
    index = 0
    while not bot.is_closed():
        try:
            await bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=statuses[index]),
                status=discord.Status.online
            )
            index = (index + 1) % len(statuses)
            await asyncio.sleep(20)
        except:
            await asyncio.sleep(10)

# =========================
# LOAD COGS
# =========================
async def load_cogs():
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print("🚀 Loading Cogs...")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Loaded: {filename}")
            except Exception as e:
                print(f"❌ Failed: {filename}\n{type(e).__name__}: {e}")
    print("━━━━━━━━━━━━━━━━━━━━━━")

# =========================
# EVENTS
# =========================
@bot.event
async def on_ready():
    # --- NEW: Initialize the Async Database ---
    try:
        await database.initialize_db()
        print("🗄️ Database Tables Initialized")
    except Exception as e:
        print(f"❌ Database Error: {e}")

    print("━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🤖 BOT ONLINE: {bot.user}")
    print(f"🌐 Servers  : {len(bot.guilds)}")
    
    # Sync Slash Commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Slash Sync Error: {e}")

    latency = round(bot.latency * 1000)
    uptime = round(time.time() - startup_time, 2)
    print(f"⚡ Ping: {latency}ms | 🚀 Startup: {uptime}s")
    print("━━━━━━━━━━━━━━━━━━━━━━")

@bot.event
async def on_guild_join(guild):
    if guild.owner:
        try:
            embed = discord.Embed(
                title="🤖 Thanks for inviting me!",
                description="Use `/help` to see all features.\n⚡ Anti-Nuke and Advanced Moderation enabled.",
                color=discord.Color.blurple()
            )
            await guild.owner.send(embed=embed)
        except:
            pass

@bot.event
async def on_command_error(ctx, error):
    error = getattr(error, "original", error)
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(f"⏳ Slow down! Try again in {round(error.retry_after, 1)}s")
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send(f"❌ You need permissions: `{', '.join(error.missing_permissions)}`")
    if isinstance(error, commands.CommandNotFound):
        return
    
    # Log unexpected errors
    traceback.print_exception(type(error), error, error.__traceback__)

# =========================
# BOT STARTUP
# =========================
async def main():
    async with bot:
        await load_cogs()
        bot.loop.create_task(status_task())
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot shutting down")
