import discord

from utils.logger import (
    get_logs,
    is_log_enabled,
    save_log
)

MOD_ACTIONS = [
    "ban",
    "kick",
    "warn",
    "mute",
    "unmute",
    "unban"
]


async def dispatch_log(
    guild,
    log_type,
    content=None,
    embed=None,
    user_id=0,
    moderator_id=0
):

    if not guild:
        return

    # =========================
    # CHECK SETTINGS
    # =========================
    enabled = await is_log_enabled(guild.id, log_type)

    if not enabled:
        return

    # =========================
    # GET CHANNELS
    # =========================
    channels = await get_logs(guild.id)

    if not channels:
        return

    mod_log_id, bot_log_id = channels

    target_channel_id = (
        mod_log_id
        if log_type in MOD_ACTIONS
        else bot_log_id
    )

    channel = guild.get_channel(target_channel_id)

    if not channel:
        return

    # =========================
    # SAVE TO DATABASE
    # =========================
    try:
        await save_log(
            guild.id,
            user_id,
            log_type,
            content or "No content provided.",
            moderator_id
        )
    except Exception as e:
        print(f"[LOG SAVE ERROR] {e}")

    # =========================
    # SEND MESSAGE
    # =========================
    try:
        if embed:
            await channel.send(
                content=content,
                embed=embed
            )
        else:
            await channel.send(content)

    except discord.Forbidden:
        print(f"[LOG PERMISSION ERROR] {guild.name}")

    except Exception as e:
        print(f"[DISPATCH ERROR] {e}")
