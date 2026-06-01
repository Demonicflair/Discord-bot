import os
import logging
import discord

from discord.ext import commands

from utils.config import (
    TOKEN,
    PREFIX,
    BOT_NAME
)

from utils.database import initialize_db


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("DemBot")

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
        "Failed importing ticket views"
    )

try:

    from cogs.giveaways import GiveawayView

    GIVEAWAY_VIEW_EXISTS = True

except Exception:

    logger.exception(
        "Failed importing giveaway views"
    )


class DemBot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.default()

        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.guild_messages = True
        intents.message_content = True

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
                users=True,
                replied_user=False
            ),

            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{BOT_NAME} Booting..."
            )
        )

        self.start_time = discord.utils.utcnow()

    async def setup_hook(self):

        logger.info(
            f"Starting {BOT_NAME}"
        )

        await initialize_db()

        loaded = 0
        failed = 0

        for file in sorted(
            os.listdir("cogs")
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

                logger.exception(
                    f"Failed loading {cog}"
                )

        logger.info(
            f"Loaded={loaded} Failed={failed}"
        )

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

        logger.info(
            "Slash commands ready"
        )

    async def on_ready(self):

        await self.change_presence(

            status=discord.Status.online,

            activity=discord.Activity(

                type=discord.ActivityType.watching,

                name=f"{len(self.guilds)} servers | /help"

            )
        )

        logger.info(

            f"Logged in as "

            f"{self.user} "

            f"({self.user.id})"

        )

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

    async def on_application_command_error(
        self,
        interaction,
        error
    ):

        logger.exception(
            "Application Error",
            exc_info=error
        )

        try:

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ Something went wrong.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ Something went wrong.",
                    ephemeral=True
                )

        except:
            pass


bot = DemBot()

bot.run(
    TOKEN,
    reconnect=True,
    log_handler=None
)
