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
    "untimeout"
}


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
    # BASIC SAFETY CHECKS
    # =========================
    if not guild:
        return

    try:

        # =========================
        # CHECK IF ENABLED
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
        channels = await get_logs(guild.id)

        if not channels:
            return

        mod_log_id, bot_log_id = channels

        # =========================
        # CHOOSE TARGET CHANNEL
        # =========================
        target_channel_id = (
            mod_log_id
            if log_type.lower() in MOD_ACTIONS
            else bot_log_id
        )

        if not target_channel_id:
            return

        channel = guild.get_channel(target_channel_id)

        if not channel:
            return

        # =========================
        # SAVE LOG TO DATABASE
        # =========================
        try:

            await save_log(
                guild_id=guild.id,
                user_id=user_id,
                log_type=log_type,
                content=content or "No details provided.",
                moderator_id=moderator_id
            )

        except Exception as error:
            print(f"[SAVE LOG ERROR] {error}")

        # =========================
        # SEND LOG MESSAGE
        # =========================
        if embed:

            await channel.send(
                content=content,
                embed=embed
            )

        else:

            await channel.send(
                content=content
            )

    except discord.Forbidden:

        print(
            f"[DISPATCH ERROR] Missing permissions in guild: {guild.name}"
        )

    except Exception as error:

        print(
            f"[DISPATCH ERROR] {error}"
        )
