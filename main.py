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
    TicketControls
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
                name="Booting Systems..."
            ),
            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
                replied_user=False
            )
        )

        self.start_time = discord.utils.utcnow()

    # =========================
    # SETUP HOOK
    # =========================

    async def setup_hook(self):

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🚀 Starting {BOT_NAME}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

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
            self.add_view(TicketControls())
            self.add_view(GiveawayView())

            print("✅ Persistent views loaded")

        except Exception:

            print("❌ Failed loading persistent views")
            traceback.print_exc()

        # =========================
        # LOAD COGS
        # =========================

        loaded = 0
        failed = 0

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📦 Loading Cogs")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

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

            except Exception:

                failed += 1

                print(f"❌ Failed → {cog}")
                traceback.print_exc()

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"✅ Loaded : {loaded}")
        print(f"❌ Failed : {failed}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

        # =========================
        # SYNC COMMANDS
        # =========================

        try:

            synced = await self.tree.sync()

            print(
                f"✅ Synced {len(synced)} commands"
            )

        except Exception:

            print("❌ Slash sync failed")
            traceback.print_exc()

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

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🤖 BOT ONLINE")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"👤 User    : {self.user}")
        print(f"🆔 ID      : {self.user.id}")
        print(f"🌍 Guilds  : {len(self.guilds)}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # =========================
    # PREFIX ERRORS
    # =========================

    async def on_command_error(
        self,
        ctx,
        error
    ):

        if hasattr(ctx.command, "on_error"):
            return

        error = getattr(
            error,
            "original",
            error
        )

        # =========================
        # UNKNOWN COMMAND
        # =========================

        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        # =========================
        # MISSING USER PERMS
        # =========================

        elif isinstance(
            error,
            commands.MissingPermissions
        ):

            return await ctx.send(
                embed=discord.Embed(
                    description=(
                        "❌ You don't have permission "
                        "to use this command."
                    ),
                    color=discord.Color.red()
                )
            )

        # =========================
        # MISSING BOT PERMS
        # =========================

        elif isinstance(
            error,
            commands.BotMissingPermissions
        ):

            perms = ", ".join(
                error.missing_permissions
            )

            return await ctx.send(
                embed=discord.Embed(
                    description=(
                        f"❌ Missing permissions:\n"
                        f"`{perms}`"
                    ),
                    color=discord.Color.red()
                )
            )

        # =========================
        # COOLDOWN
        # =========================

        elif isinstance(
            error,
            commands.CommandOnCooldown
        ):

            return await ctx.send(
                embed=discord.Embed(
                    description=(
                        f"⏳ Try again in "
                        f"`{round(error.retry_after, 1)}s`"
                    ),
                    color=discord.Color.orange()
                )
            )

        # =========================
        # MISSING ARGUMENT
        # =========================

        elif isinstance(
            error,
            commands.MissingRequiredArgument
        ):

            return await ctx.send(
                embed=discord.Embed(
                    description=(
                        f"⚠️ Missing parameter:\n"
                        f"`{error.param.name}`"
                    ),
                    color=discord.Color.orange()
                )
            )

        # =========================
        # BAD ARGUMENT
        # =========================

        elif isinstance(
            error,
            (
                commands.BadArgument,
                commands.MemberNotFound,
                commands.RoleNotFound,
                commands.ChannelNotFound
            )
        ):

            return await ctx.send(
                embed=discord.Embed(
                    description="❌ Invalid argument provided.",
                    color=discord.Color.red()
                )
            )

        # =========================
        # UNHANDLED ERROR
        # =========================

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("❌ COMMAND ERROR")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__
        )

        try:

            await ctx.send(
                embed=discord.Embed(
                    title="❌ Unexpected Error",
                    description=(
                        "An unexpected error occurred.\n"
                        "Check Railway logs."
                    ),
                    color=discord.Color.red()
                )
            )

        except:
            pass

    # =========================
    # SLASH ERRORS
    # =========================

    async def on_application_command_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("❌ SLASH COMMAND ERROR")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__
        )

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
# CREATE BOT
# =========================

bot = DemBot()

# =========================
# START BOT
# =========================

if __name__ == "__main__":

    if not TOKEN:

        raise ValueError(
            "TOKEN missing inside .env"
        )

    try:

        bot.run(
            TOKEN,
            reconnect=True,
            log_handler=None
        )

    except KeyboardInterrupt:

        print("\n🛑 Bot shutdown")

    except Exception:

        print("\n❌ Fatal Startup Error")
        traceback.print_exc()
