import traceback
import discord

from utils.logger import (
    get_logs,
    is_log_enabled,
    save_log
)

# =========================
# MODERATION ACTION TYPES
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
# DEFAULT COLORS
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
# SAFE EMBED CREATOR
# =========================

def build_embed(
    log_type: str,
    content: str
):

    return discord.Embed(
        description=content,
        color=LOG_COLORS.get(
            log_type.lower(),
            0x2b2d31
        )
    )

# =========================
# CENTRAL LOG DISPATCHER
# =========================

async def dispatch_log(
    guild: discord.Guild,
    log_type: str,
    content: str = None,
    embed: discord.Embed = None,
    user_id: int = 0,
    moderator_id: int = 0
):

    # =========================
    # BASIC SAFETY
    # =========================

    if not guild:
        return

    if not log_type:
        return

    try:

        # =========================
        # CHECK ENABLED
        # =========================

        enabled = await is_log_enabled(
            guild.id,
            log_type
        )

        if not enabled:
            return

        # =========================
        # FETCH LOG CHANNELS
        # =========================

        channels = await get_logs(
            guild.id
        )

        if not channels:
            return

        mod_log_id, bot_log_id = channels

        # =========================
        # PICK TARGET CHANNEL
        # =========================

        target_channel_id = (

            mod_log_id

            if log_type.lower() in MOD_ACTIONS

            else bot_log_id

        )

        if not target_channel_id:
            return

        channel = guild.get_channel(
            target_channel_id
        )

        if not channel:
            return

        # =========================
        # BOT PERMISSION CHECK
        # =========================

        permissions = channel.permissions_for(
            guild.me
        )

        if not permissions.send_messages:
            return

        if embed and not permissions.embed_links:
            embed = None

        # =========================
        # SAVE DATABASE LOG
        # =========================

        try:

            await save_log(

                guild_id=guild.id,
                user_id=user_id,
                log_type=log_type,
                content=content or "No details provided.",
                moderator_id=moderator_id

            )

        except Exception:

            print("\n[SAVE LOG ERROR]")
            traceback.print_exc()

        # =========================
        # AUTO EMBED
        # =========================

        if not embed:

            embed = build_embed(
                log_type,
                content or "No details provided."
            )

        # =========================
        # FOOTER
        # =========================

        footer_parts = []

        if user_id:
            footer_parts.append(
                f"User ID: {user_id}"
            )

        if moderator_id:
            footer_parts.append(
                f"Moderator ID: {moderator_id}"
            )

        if footer_parts:

            embed.set_footer(
                text=" • ".join(footer_parts)
            )

        # =========================
        # TIMESTAMP
        # =========================

        embed.timestamp = discord.utils.utcnow()

        # =========================
        # SEND LOG
        # =========================

        await channel.send(
            embed=embed
        )

    # =========================
    # MISSING PERMISSIONS
    # =========================

    except discord.Forbidden:

        print(
            f"[DISPATCH ERROR] Missing permissions in guild: {guild.name}"
        )

    # =========================
    # CHANNEL NOT FOUND
    # =========================

    except discord.NotFound:

        print(
            f"[DISPATCH ERROR] Channel not found in guild: {guild.name}"
        )

    # =========================
    # UNKNOWN ERROR
    # =========================

    except Exception:

        print("\n[DISPATCH ERROR]")
        traceback.print_exc()
