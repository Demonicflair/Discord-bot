import logging
import discord

from utils.logger import (
    get_logs,
    is_log_enabled,
    save_log
)

logger = logging.getLogger(
    "DemBot.Dispatch"
)

# =========================
# MOD ACTIONS
# =========================

MOD_ACTIONS = {

    "ban",
    "unban",
    "kick",
    "warn",
    "mute",
    "unmute",
    "timeout",
    "untimeout",
    "clear",
    "lock",
    "unlock"

}

# =========================
# COLORS
# =========================

LOG_COLORS = {

    "ban": discord.Color.red(),

    "kick": discord.Color.orange(),

    "warn": discord.Color.gold(),

    "unban": discord.Color.green(),

    "mute": discord.Color.dark_orange(),

    "unmute": discord.Color.green(),

    "timeout": discord.Color.orange(),

    "untimeout": discord.Color.green(),

    "clear": discord.Color.blurple(),

    "ticket_create": discord.Color.blurple(),

    "ticket_close": discord.Color.red(),

    "giveaway": discord.Color.purple(),

    "antinuke": discord.Color.dark_red(),

    "join": discord.Color.green(),

    "leave": discord.Color.red()

}


# =========================
# EMBED BUILDER
# =========================

def build_embed(
    log_type: str,
    content: str
):

    return discord.Embed(

        description=content,

        color=LOG_COLORS.get(

            log_type.lower(),

            0x2B2D31

        )

    )


# =========================
# CENTRAL DISPATCH
# =========================

async def dispatch_log(

    guild: discord.Guild,

    log_type: str,

    content: str = None,

    embed: discord.Embed = None,

    user_id: int = 0,

    moderator_id: int = 0

):

    if not guild:

        return

    if not log_type:

        return

    try:

        enabled = await is_log_enabled(

            guild.id,

            log_type

        )

        if not enabled:

            return

        logs = await get_logs(

            guild.id

        )

        if not logs:

            return

        target_channel_id = (

            logs["mod_log"]

            if log_type.lower()

            in MOD_ACTIONS

            else logs["bot_log"]

        )

        if not target_channel_id:

            return

        channel = guild.get_channel(

            target_channel_id

        )

        if not channel:

            return

        me = guild.me or guild.get_member(

            guild._state.self_id

        )

        if not me:

            return

        perms = channel.permissions_for(

            me

        )

        if not perms.send_messages:

            return

        if embed and not perms.embed_links:

            embed = None

        log_content = (

            content

            or

            "No details provided."

        )

        try:

            await save_log(

                guild_id=guild.id,

                user_id=user_id,

                log_type=log_type,

                content=log_content,

                moderator_id=moderator_id

            )

        except Exception:

            logger.exception(

                "Failed saving log"

            )

        if embed is None:

            embed = build_embed(

                log_type,

                log_content

            )

        footer = []

        if user_id:

            footer.append(

                f"User ID: {user_id}"

            )

        if moderator_id:

            footer.append(

                f"Moderator ID: {moderator_id}"

            )

        if footer:

            embed.set_footer(

                text=" • ".join(

                    footer

                )

            )

        embed.timestamp = (

            discord.utils.utcnow()

        )

        await channel.send(

            embed=embed

        )

    except discord.Forbidden:

        logger.warning(

            f"No permission "

            f"{guild.id}"

        )

    except discord.NotFound:

        logger.warning(

            f"Channel missing "

            f"{guild.id}"

        )

    except Exception:

        logger.exception(

            "Dispatch failed"

            )
