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

logger = logging.getLogger(
    "DemBot"
)


class DemBot(commands.Bot):

    def __init__(self):

        intents = discord.Intents.default()

        intents.guilds = True
        intents.members = True
        intents.messages = True
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

                name=f"{BOT_NAME} Starting..."

            )

        )

        self.start_time = discord.utils.utcnow()

    # ===================================
    # STARTUP
    # ===================================

    async def setup_hook(self):

        logger.info(
            "Initializing database..."
        )

        await initialize_db()

        loaded = 0
        failed = 0

        logger.info(
            "Loading cogs..."
        )

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

            f"Cogs Loaded: "

            f"{loaded} "

            f"| Failed: "

            f"{failed}"

        )

        logger.info(
            "Startup completed."
        )

    # ===================================
    # READY
    # ===================================

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

    # ===================================
    # PREFIX COMMAND ERRORS
    # ===================================

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

    # ===================================
    # SLASH ERRORS
    # ===================================

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
