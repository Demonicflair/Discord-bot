import os
import discord
from discord.ext import commands

from utils.config import TOKEN, PREFIX
from utils.database import initialize_db

# =========================
# PERSISTENT VIEWS
# =========================
from cogs.tickets import (
    TicketView,
    TicketControlView
)

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
            case_insensitive=True,
            strip_after_prefix=True
        )

    # =========================
    # STARTUP SYSTEM
    # =========================
    async def setup_hook(self):

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🚀 Starting Dem System...")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # =========================
        # DATABASE INIT
        # =========================
        await initialize_db()

        print("✅ Database initialized")

        # =========================
        # REGISTER PERSISTENT VIEWS
        # =========================
        try:

            self.add_view(TicketView())
            self.add_view(TicketControlView())

            print("✅ Persistent views registered")

        except Exception as error:

            print(f"❌ Persistent View Error: {error}")

        # =========================
        # LOAD COGS
        # =========================
        loaded = 0
        failed = 0

        for file in os.listdir("./cogs"):

            if not file.endswith(".py"):
                continue

            if file.startswith("_"):
                continue

            cog_name = file[:-3]

            try:

                await self.load_extension(
                    f"cogs.{cog_name}"
                )

                loaded += 1

                print(f"✅ Loaded Cog: {cog_name}")

            except Exception as error:

                failed += 1

                print(f"❌ Failed Cog: {cog_name}")
                print(f"   ↳ {error}")

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"✅ Loaded: {loaded}")
        print(f"❌ Failed: {failed}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # =========================
        # SLASH COMMAND SYNC
        # =========================
        try:

            synced = await self.tree.sync()

            print(
                f"✅ Synced {len(synced)} application commands"
            )

        except Exception as error:

            print(
                f"❌ Slash Sync Error: {error}"
            )

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

        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🤖 Logged in as: {self.user}")
        print(f"🆔 ID: {self.user.id}")
        print(f"🌍 Guilds: {len(self.guilds)}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # =========================
    # GLOBAL ERROR HANDLER
    # =========================
    async def on_command_error(
        self,
        ctx,
        error
    ):

        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        elif isinstance(
            error,
            commands.MissingPermissions
        ):

            return await ctx.send(
                "❌ You don't have permission to use this command."
            )

        elif isinstance(
            error,
            commands.BotMissingPermissions
        ):

            return await ctx.send(
                "❌ I am missing required permissions."
            )

        elif isinstance(
            error,
            commands.MissingRequiredArgument
        ):

            return await ctx.send(
                f"❌ Missing argument: `{error.param.name}`"
            )

        elif isinstance(
            error,
            commands.CommandOnCooldown
        ):

            return await ctx.send(
                f"⏳ Try again in `{round(error.retry_after, 1)}s`"
            )

        print(f"[COMMAND ERROR] {error}")

# =========================
# START BOT
# =========================
bot = DemBot()

if __name__ == "__main__":

    if not TOKEN:

        raise ValueError(
            "TOKEN not found in .env file"
        )

    bot.run(
        TOKEN,
        reconnect=True
    )
