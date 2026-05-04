import discord
from discord.ext import commands
import os
import asyncio
import config

# 🔹 Intents
intents = discord.Intents.all()

# 🔹 Bot Class
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # ✅ Load all cogs
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{file[:-3]}")
                    print(f"Loaded cog: {file}")
                except Exception as e:
                    print(f"Failed to load {file}: {e}")

        # ✅ Sync slash commands
        try:
            await self.tree.sync()
            print("Slash commands synced")
        except Exception as e:
            print(f"Slash sync error: {e}")

# 🔹 Create bot
bot = MyBot()

# 🔹 Ready event
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# 🔹 Run bot
async def main():
    async with bot:
        await bot.start(config.TOKEN)

asyncio.run(main())
