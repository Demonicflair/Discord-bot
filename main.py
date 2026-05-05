import discord
from discord.ext import commands
import asyncio
import os
import config

# =========================
# 🔹 INTENTS
# =========================
intents = discord.Intents.all()


# =========================
# 🔹 BOT CLASS
# =========================
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # ✅ Load all cogs automatically
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
            print("✅ Slash commands synced")
        except Exception as e:
            print(f"❌ Sync error: {e}")


# =========================
# 🔹 CREATE BOT
# =========================
bot = MyBot()


# =========================
# 🔹 READY EVENT
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    # 🔥 IMPORTANT: Persistent Views (fixes interaction failed)
    try:
        from cogs.tickets import TicketView, TicketControlView

        bot.add_view(TicketView())
        bot.add_view(TicketControlView())

        print("✅ Ticket views loaded")

    except Exception as e:
        print(f"❌ Ticket view error: {e}")


# =========================
# 🔹 ERROR HANDLER (ANTI-CRASH)
# =========================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("❌ You don't have permission.")

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send("❌ Missing arguments.")

    if isinstance(error, commands.CommandNotFound):
        return

    await ctx.send(f"❌ Error: {error}")


# =========================
# 🔹 RUN BOT
# =========================
async def main():
    async with bot:
        await bot.start(config.TOKEN)


asyncio.run(main())
