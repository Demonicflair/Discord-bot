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
            print("Slash commands synced globally")
        except Exception as e:
            print(f"Global sync error: {e}")

        # ⚡ OPTIONAL (FASTER TESTING - REPLACE WITH YOUR SERVER ID)
        # guild = discord.Object(id=123456789012345678)
        # await self.tree.sync(guild=guild)


# 🔹 Create bot
bot = MyBot()


# 🔹 Ready Event (IMPORTANT FOR TICKETS)
@bot.event
async def on_ready():
    try:
        # Import ticket views here (avoids errors)
        from cogs.tickets import TicketView, TicketControlView

        # ✅ Persistent Views (fixes interaction failed forever)
        bot.add_view(TicketView())
        bot.add_view(TicketControlView())

    except Exception as e:
        print(f"Ticket view error: {e}")

    print(f"✅ Logged in as {bot.user}")


# 🔹 Run bot
async def main():
    async with bot:
        await bot.start(config.TOKEN)


asyncio.run(main())
