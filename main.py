import os
import discord
from discord.ext import commands

from utils.config import TOKEN, PREFIX
from utils.database import initialize_db

# Persistent Views
from cogs.tickets import TicketView, TicketControlView

# =========================
# BOT CLASS
# =========================

class DemBot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.all()

        super().__init__(
            command_prefix=commands.when_mentioned_or(PREFIX),
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    # =========================
    # STARTUP
    # =========================

    async def setup_hook(self):

        print("━━━━━━━━━━━━━━━━━━━━")
        print("Starting Dem System...")
        print("━━━━━━━━━━━━━━━━━━━━")

        # =========================
        # DATABASE
        # =========================

        await initialize_db()
        print("✅ Database initialized")

        # =========================
        # PERSISTENT VIEWS
        # =========================

        self.add_view(TicketView())
        self.add_view(TicketControlView())

        print("✅ Persistent views loaded")

        # =========================
        # LOAD COGS
        # =========================

        loaded = 0

        for file in os.listdir("./cogs"):

            if file.endswith(".py"):

                try:
                    await self.load_extension(f"cogs.{file[:-3]}")

                    print(f"✅ Loaded Cog: {file}")
                    loaded += 1

                except Exception as e:
                    print(f"❌ Failed {file}")
                    print(f"   Error: {e}")

        print(f"✅ Total Loaded Cogs: {loaded}")

        # =========================
        # SYNC COMMANDS
        # =========================

        try:
            synced = await self.tree.sync()

            print(f"✅ Synced {len(synced)} slash commands")

        except Exception as e:
            print(f"❌ Slash Sync Failed: {e}")

        print("━━━━━━━━━━━━━━━━━━━━")
        print("Dem System Ready")
        print("━━━━━━━━━━━━━━━━━━━━")

    # =========================
    # READY EVENT
    # =========================

    async def on_ready(self):

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers"
        )

        await self.change_presence(
            status=discord.Status.online,
            activity=activity
        )

        print(f"🚀 Logged in as: {self.user}")
        print(f"🆔 Bot ID: {self.user.id}")
        print(f"🌍 Servers: {len(self.guilds)}")

# =========================
# BOT START
# =========================

bot = DemBot()

if __name__ == "__main__":

    if not TOKEN:
        raise ValueError("TOKEN not found in .env file")

    bot.run(TOKEN)
