import os
import traceback
import discord
import asyncio

from discord.ext import commands

from utils.config import (
    TOKEN,
    PREFIX,
    BOT_NAME,
    BRAND_COLOR
)

from utils.database import initialize_db

# =========================
# PERSISTENT VIEWS
# =========================

from cogs.tickets import (
    TicketView,
    TicketControlView
)

from cogs.giveaway import GiveawayView

# =========================
# MAIN BOT CLASS
# =========================

class DemBot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.all()

        super().__init__(
            command_prefix=commands.when_mentioned_or(PREFIX),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Starting Systems..."
            )
        )

        self.start_time = discord.utils.utcnow()

    # =========================
    # STARTUP SYSTEM
    # =========================

    async def setup_hook(self):

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🚀 Booting {BOT_NAME}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        # =========================
        # DATABASE
        # =========================

        try:

            await initialize_db()

            print("✅ Database initialized")

        except Exception as error:

            print(f"❌ Database Error:\n{error}")

        # =========================
        # PERSISTENT VIEWS
        # =========================

        try:

            self.add_view(TicketView())
            self.add_view(TicketControlView())
            self.add_view(GiveawayView())

            print("✅ Persistent views loaded")

        except Exception as error:

            print(f"❌ Persistent View Error:\n{error}")

        # =========================
        # LOAD COGS
        # =========================

        loaded = 0
        failed = 0

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📦 Loading Extensions")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        for file in sorted(os.listdir("./cogs")):

            if not file.endswith(".py"):
                continue

            if file.startswith("_"):
                continue

            cog = file[:-3]

            try:

                await self.load_extension(
                    f"cogs.{cog}"
                )

                loaded += 1

                print(f"✅ Loaded → {cog}")

            except Exception as error:

                failed += 1

                print(f"❌ Failed → {cog}")
                print(traceback.format_exc())

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"✅ Total Loaded : {loaded}")
        print(f"❌ Total Failed : {failed}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        # =========================
        # SYNC SLASH COMMANDS
        # =========================

        try:

            synced = await self.tree.sync()

            print(
                f"✅ Synced {len(synced)} slash commands"
            )

        except Exception as error:

            print(f"❌ Slash Sync Error:\n{error}")

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

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🤖 BOT ONLINE")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"👤 Logged in as : {self.user}")
        print(f"🆔 Bot ID       : {self.user.id}")
        print(f"🌍 Guilds       : {len(self.guilds)}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # =========================
    # GLOBAL COMMAND ERROR
    # =========================

    async def on_command_error(
        self,
        ctx,
        error
    ):

        if hasattr(ctx.command, "on_error"):
            return

        # Ignore unknown commands
        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        # Missing User Permission
        elif isinstance(
            error,
            commands.MissingPermissions
        ):

            embed = discord.Embed(
                title="❌ Missing Permissions",
                description=(
                    "You don't have permission "
                    "to use this command."
                ),
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        # Missing Bot Permission
        elif isinstance(
            error,
            commands.BotMissingPermissions
        ):

            perms = ", ".join(error.missing_permissions)

            embed = discord.Embed(
                title="❌ Bot Missing Permissions",
                description=f"I need:\n`{perms}`",
                color=discord.Color.red()
            )

            return await ctx.send(embed=embed)

        # Missing Argument
        elif isinstance(
            error,
            commands.MissingRequiredArgument
        ):

            embed = discord.Embed(
                title="⚠️ Missing Argument",
                description=(
                    f"Missing parameter:\n"
                    f"`{error.param.name}`"
                ),
                color=discord.Color.orange()
            )

            return await ctx.send(embed=embed)

        # Cooldown
        elif isinstance(
            error,
            commands.CommandOnCooldown
        ):

            embed = discord.Embed(
                title="⏳ Slow Down",
                description=(
                    f"Try again in "
                    f"`{round(error.retry_after, 1)}s`"
                ),
                color=discord.Color.gold()
            )

            return await ctx.send(embed=embed)

        # Member Not Found
        elif isinstance(
            error,
            commands.MemberNotFound
        ):

            return await ctx.send(
                embed=discord.Embed(
                    description="❌ Member not found.",
                    color=discord.Color.red()
                )
            )

        # Bad Argument
        elif isinstance(
            error,
            commands.BadArgument
        ):

            return await ctx.send(
                embed=discord.Embed(
                    description="❌ Invalid argument provided.",
                    color=discord.Color.red()
                )
            )

        # Unknown Error
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("❌ COMMAND ERROR")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        traceback.print_exception(
            type(error),
            error,
            error.__traceback__
        )

        embed = discord.Embed(
            title="❌ Unexpected Error",
            description=(
                "An unexpected error occurred.\n"
                "Check console logs for details."
            ),
            color=discord.Color.red()
        )

        try:
            await ctx.send(embed=embed)

        except:
            pass

    # =========================
    # APPLICATION COMMAND ERRORS
    # =========================

    async def on_application_command_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        print(f"[SLASH ERROR] {error}")

        try:

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ An error occurred.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ An error occurred.",
                    ephemeral=True
                )

        except:
            pass


# =========================
# START BOT
# =========================

bot = DemBot()

# =========================
# RUN CLIENT
# =========================

if __name__ == "__main__":

    if not TOKEN:

        raise ValueError(
            "TOKEN not found inside .env"
        )

    try:

        bot.run(
            TOKEN,
            reconnect=True,
            log_handler=None
        )

    except KeyboardInterrupt:

        print("\n🛑 Bot shutdown requested")

    except Exception as error:

        print(f"\n❌ Fatal Error:\n{error}")
