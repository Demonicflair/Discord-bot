import os
import traceback
import discord
import asyncio
import logging

from discord.ext import commands

from utils.config import (
    TOKEN,
    PREFIX,
    BOT_NAME,
    BRAND_COLOR
)

from utils.database import initialize_db

# =========================
# LOGGING SETUP
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("DemBot")

# =========================
# OPTIONAL IMPORTS
# =========================

try:

    from cogs.tickets import (
        TicketView,
        TicketControls
    )

    TICKET_VIEWS = True

except Exception:

    TICKET_VIEWS = False

    logger.exception(
        "Ticket views failed to import"
    )

try:

    from cogs.giveaways import GiveawayView

    GIVEAWAY_VIEW_EXISTS = True

except Exception:

    GIVEAWAY_VIEW_EXISTS = False

    logger.exception(
        "Giveaway view failed to import"
    )

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

            owner_ids=set(),

            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
                replied_user=False
            ),

            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Booting Systems..."
            )

        )

        self.start_time = discord.utils.utcnow()

    # =========================
    # SETUP HOOK
    # =========================

    async def setup_hook(self):

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"Starting {BOT_NAME}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # =========================
        # DATABASE
        # =========================

        try:

            await initialize_db()

            logger.info(
                "Database initialized"
            )

        except Exception:

            logger.exception(
                "Database initialization failed"
            )

        # =========================
        # LOAD COGS
        # =========================

        loaded = 0
        failed = 0

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("Loading Cogs")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        if not os.path.exists("./cogs"):

            logger.error(
                "cogs folder not found"
            )

            return

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

                logger.info(
                    f"Loaded → {cog}"
                )

            except Exception as e:

                failed += 1

                logger.error(
                    f"Failed loading → {cog}"
                )

                logger.error(
                    f"ERROR: {e}"
                )

                traceback.print_exc()

        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"Loaded : {loaded}")
        logger.info(f"Failed : {failed}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # =========================
        # PERSISTENT VIEWS
        # =========================

        try:

            if TICKET_VIEWS:

                self.add_view(
                    TicketView()
                )

                self.add_view(
                    TicketControls()
                )

                logger.info(
                    "Ticket views loaded"
                )

            if GIVEAWAY_VIEW_EXISTS:

                self.add_view(
                    GiveawayView()
                )

                logger.info(
                    "Giveaway view loaded"
                )

        except Exception:

            logger.exception(
                "Persistent view loading failed"
            )

        # =========================
        # SLASH SYNC
        # =========================

        try:

            synced = await self.tree.sync()

            logger.info(
                f"Synced {len(synced)} slash commands"
            )

        except Exception:

            logger.exception(
                "Slash command sync failed"
            )

    # =========================
    # READY EVENT
    # =========================

    async def on_ready(self):

        try:

            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers"
            )

            await self.change_presence(

                status=discord.Status.online,

                activity=activity

            )

            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("BOT ONLINE")
            logger.info(f"User   : {self.user}")
            logger.info(f"ID     : {self.user.id}")
            logger.info(f"Guilds : {len(self.guilds)}")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        except Exception:

            logger.exception(
                "Failed during on_ready"
            )

    # =========================
    # GUILD JOIN EVENT
    # =========================

    async def on_guild_join(
        self,
        guild
    ):

        logger.info(
            f"Joined guild → {guild.name} ({guild.id})"
        )

    # =========================
    # GUILD REMOVE EVENT
    # =========================

    async def on_guild_remove(
        self,
        guild
    ):

        logger.info(
            f"Removed from guild → {guild.name} ({guild.id})"
        )

    # =========================
    # PREFIX ERRORS
    # =========================

    async def on_command_error(
        self,
        ctx,
        error
    ):

        if hasattr(
            ctx.command,
            "on_error"
        ):
            return

        error = getattr(
            error,
            "original",
            error
        )

        embed = None

        # =========================
        # UNKNOWN COMMAND
        # =========================

        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        # =========================
        # USER MISSING PERMS
        # =========================

        elif isinstance(
            error,
            commands.MissingPermissions
        ):

            embed = discord.Embed(

                description=(
                    "❌ You don't have permission "
                    "to use this command."
                ),

                color=discord.Color.red()

            )

        # =========================
        # BOT MISSING PERMS
        # =========================

        elif isinstance(
            error,
            commands.BotMissingPermissions
        ):

            perms = ", ".join(
                error.missing_permissions
            )

            embed = discord.Embed(

                description=(
                    f"❌ I need these permissions:\n"
                    f"`{perms}`"
                ),

                color=discord.Color.red()

            )

        # =========================
        # COMMAND COOLDOWN
        # =========================

        elif isinstance(
            error,
            commands.CommandOnCooldown
        ):

            embed = discord.Embed(

                description=(
                    f"⏳ Try again in "
                    f"`{round(error.retry_after, 1)}s`"
                ),

                color=discord.Color.orange()

            )

        # =========================
        # MISSING ARGUMENT
        # =========================

        elif isinstance(
            error,
            commands.MissingRequiredArgument
        ):

            embed = discord.Embed(

                description=(
                    f"⚠️ Missing parameter:\n"
                    f"`{error.param.name}`"
                ),

                color=discord.Color.orange()

            )

        # =========================
        # BAD ARGUMENTS
        # =========================

        elif isinstance(
            error,
            (
                commands.BadArgument,
                commands.MemberNotFound,
                commands.RoleNotFound,
                commands.ChannelNotFound,
                commands.UserNotFound
            )
        ):

            embed = discord.Embed(

                description=(
                    "❌ Invalid argument provided."
                ),

                color=discord.Color.red()

            )

        # =========================
        # CHECK FAILURE
        # =========================

        elif isinstance(
            error,
            commands.CheckFailure
        ):

            embed = discord.Embed(

                description=(
                    "❌ You cannot use this command."
                ),

                color=discord.Color.red()

            )

        # =========================
        # UNKNOWN ERROR
        # =========================

        else:

            logger.exception(
                "Unhandled prefix command error",
                exc_info=error
            )

            embed = discord.Embed(

                title="❌ Unexpected Error",

                description=(
                    "Something went wrong while "
                    "running this command."
                ),

                color=discord.Color.red()

            )

        try:

            if embed:

                await ctx.send(
                    embed=embed,
                    delete_after=15
                )

        except Exception:

            logger.exception(
                "Failed sending error embed"
            )

    # =========================
    # SLASH ERRORS
    # =========================

    async def on_application_command_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        logger.exception(
            "Unhandled slash command error",
            exc_info=error
        )

        embed = discord.Embed(

            title="❌ Error",

            description=(
                "Something went wrong while "
                "running this command."
            ),

            color=discord.Color.red()

        )

        try:

            if interaction.response.is_done():

                await interaction.followup.send(
                    embed=embed,
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )

        except Exception:

            logger.exception(
                "Failed sending slash error message"
            )

    # =========================
    # MESSAGE EVENT
    # =========================

    async def on_message(
        self,
        message
    ):

        if message.author.bot:
            return

        await self.process_commands(
            message
        )


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

        logger.info(
            "Bot shutdown requested"
        )

    except Exception:

        logger.exception(
            "Fatal startup error"
        )
