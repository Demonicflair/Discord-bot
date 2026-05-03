import discord, os, asyncio
from discord.ext import commands
import config

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

async def load():
    for f in os.listdir("./cogs"):
        if f.endswith(".py"):
            await bot.load_extension(f"cogs.{f[:-3]}")

async def main():
    await load()
    await bot.start(config.TOKEN)

asyncio.run(main())