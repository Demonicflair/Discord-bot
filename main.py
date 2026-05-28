import os
import logging
import traceback
import discord

from discord.ext import commands

from utils.config import (
    TOKEN,
    PREFIX,
    BOT_NAME
)

from utils.database import initialize_db

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("DemBot")


# =========================
# OPTIONAL VIEW IMPORTS
# =========================

TICKET_VIEWS = False
GIVEAWAY_VIEW_EXISTS = False

try:

    from cogs.tickets import (
        TicketView,
        TicketControls
    )

    TICKET_VIEWS = True

except Exception:

    logger.exception(
        "Ticket views failed importing"
    )

try:

    from cogs.giveaways import GiveawayView

    GIVEAWAY_VIEW_EXISTS = True

except Exception:

    logger.exception(
        "Giveaway view failed importing"
    )


# =========================
# BOT CLASS
# =========================

class DemBot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.default()

        intents.guilds = True
        intents.members = True
        intents.message_content = True
        intents.messages = True
        intents.guild_messages = True

        super().__init__(

            command_prefix=commands.when_mentioned_or(
                PREFIX
            ),

            intents=intents,

            help_command=None,

            case_insensitive=True,

            strip_after_prefix=True,

            allowed_mentions=discord.AllowedMentions(
                everyone=False,
                roles=False,
                replied_user=False
            ),

            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Starting..."
            )
        )

        self.start_time = discord.utils.utcnow()

    # =========================
    # SETUP
    # =========================

    async def setup_hook(self):

        logger.info(
            f"Starting {BOT_NAME}"
        )

        # DATABASE

        try:

            await initialize_db()

            logger.info(
                "Database initialized"
            )

        except Exception:

            logger.exception(
                "Database failed"

            )

            raise

        # LOAD COGS

        loaded = 0
        failed = 0

        cog_folder = os.path.join(
            os.getcwd(),
            "cogs"
        )

        for file in sorted(
            os.listdir(cog_folder)
        ):

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
                    f"Loaded {cog}"
                )

            except Exception:

                failed += 1

                logger.error(
                    f"Failed {cog}"
                )

                traceback.print_exc()

        logger.info(
            f"Cogs Loaded={loaded} Failed={failed}"
        )

        # PERSISTENT VIEWS

        try:

            if TICKET_VIEWS:

                self.add_view(
                    TicketView()
                )

                self.add_view(
                    TicketControls()
                )

            if GIVEAWAY_VIEW_EXISTS:

                self.add_view(
                    GiveawayView()
                )

        except Exception:

            logger.exception(
                "Persistent views failed"
            )

    # =========================
    # READY
    # =========================

    async def on_ready(self):

        await self.change_presence(

            status=discord.Status.online,

            activity=discord.Activity(

                type=discord.ActivityType.watching,

                name=f"{len(self.guilds)} servers"

            )
        )

        logger.info(
            f"Online as {self.user}"
        )

    # =========================
    # MESSAGE
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
    # GLOBAL PREFIX ERRORS
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

        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        logger.exception(
            "Command Error",
            exc_info=error
        )

        try:

            await ctx.send(
                "❌ Something went wrong.",
                delete_after=10
            )

        except:
            pass

    # =========================
    # GLOBAL SLASH ERRORS
    # =========================

    async def on_application_command_error(
        self,
        interaction,
        error
    ):

        logger.exception(
            "Slash Error",
            exc_info=error
        )

        try:

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ Error occurred.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ Error occurred.",
                    ephemeral=True
                )

        except:
            pass


# =========================
# START
# =========================

bot = DemBot()

if __name__ == "__main__":

    bot.run(
        TOKEN,
        reconnect=True,
        log_handler=None
            )
