import discord
from discord.ext import commands
import asyncio
import config
import os

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# =========================
# BOT SETUP
# =========================
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# =========================
# LOAD COGS
# =========================
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded: {filename}")
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")

# =========================
# ERROR HANDLER
# =========================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument.\nUsage: `{ctx.prefix}{ctx.command} {ctx.command.signature}`")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send("❌ Error occurred.")
        print(error)

# =========================
# START BOT
# =========================
async def main():
    async with bot:
        await load_cogs()
        await bot.start(config.TOKEN)

asyncio.run(main())
