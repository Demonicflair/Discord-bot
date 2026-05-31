import discord
from typing import Optional, List, Dict, Any

from utils.database import get_db
from utils.config import BRAND_COLOR

# ======================================
# CACHE
# ======================================

_settings_cache: dict = {}

MOD_LOG_TYPES = {
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

# ======================================
# GET LOG CHANNELS
# ======================================

async def get_logs(guild_id: int) -> Optional[dict]:

    async with await get_db() as db:

        async with db.execute(
            """
            SELECT mod_log, bot_log
            FROM log_channels
            WHERE guild_id=?
            """,
            (guild_id,)
        ) as cursor:

            row = await cursor.fetchone()

    if not row:
        return None

    return {
        "mod_log": row["mod_log"],
        "bot_log": row["bot_log"]
    }


# ======================================
# SET LOG CHANNELS
# ======================================

async def set_log_channels(
    guild_id: int,
    mod_log: Optional[int] = None,
    bot_log: Optional[int] = None
):

    existing = await get_logs(guild_id)

    if existing:

        mod_log = existing["mod_log"] if mod_log is None else mod_log
        bot_log = existing["bot_log"] if bot_log is None else bot_log

    async with await get_db() as db:

        await db.execute(
            """
            INSERT OR REPLACE INTO log_channels
            (guild_id, mod_log, bot_log)
            VALUES (?, ?, ?)
            """,
            (
                guild_id,
                mod_log,
                bot_log
            )
        )

        await db.commit()


# ======================================
# SAVE LOG
# ======================================

async def save_log(
    guild_id: int,
    user_id: int,
    log_type: str,
    content: str,
    moderator_id: int = 0
) -> int:

    async with await get_db() as db:

        cursor = await db.execute(
            """
            INSERT INTO logs_data
            (
                guild_id,
                user_id,
                moderator_id,
                type,
                content
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                moderator_id,
                log_type.lower(),
                content
            )
        )

        await db.commit()

        return cursor.lastrowid


# ======================================
# SEND LOG
# ======================================

async def send_log(
    guild: discord.Guild,
    log_type: str,
    embed: discord.Embed
):

    logs = await get_logs(guild.id)

    if not logs:
        return

    channel_id = (

        logs["mod_log"]

        if log_type.lower() in MOD_LOG_TYPES

        else logs["bot_log"]

    )

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if not channel:
        return

    me = guild.me

    if not me:
        return

    perms = channel.permissions_for(me)

    if not perms.send_messages:
        return

    try:

        await channel.send(embed=embed)

    except (
        discord.Forbidden,
        discord.NotFound,
        discord.HTTPException
    ):

        pass


# ======================================
# LOG ENABLED
# ======================================

async def is_log_enabled(
    guild_id: int,
    log_type: str
) -> bool:

    key = (
        guild_id,
        log_type.lower()
    )

    if key in _settings_cache:

        return _settings_cache[key]

    async with await get_db() as db:

        async with db.execute(
            """
            SELECT enabled
            FROM log_settings
            WHERE guild_id=?
            AND log_type=?
            """,
            key
        ) as cursor:

            data = await cursor.fetchone()

    enabled = True if data is None else bool(data["enabled"])

    _settings_cache[key] = enabled

    return enabled


# ======================================
# SET LOG STATE
# ======================================

async def set_log_state(
    guild_id: int,
    log_type: str,
    state: bool
):

    key = (
        guild_id,
        log_type.lower()
    )

    async with await get_db() as db:

        await db.execute(
            """
            INSERT OR REPLACE INTO log_settings
            (
                guild_id,
                log_type,
                enabled
            )
            VALUES (?, ?, ?)
            """,
            (
                guild_id,
                log_type.lower(),
                int(state)
            )
        )

        await db.commit()

    _settings_cache[key] = state


# ======================================
# USER HISTORY
# ======================================

async def get_user_history(
    guild_id: int,
    user_id: int,
    limit: int = 10
):

    async with await get_db() as db:

        async with db.execute(
            """
            SELECT *
            FROM logs_data
            WHERE guild_id=?
            AND user_id=?
            ORDER BY case_id DESC
            LIMIT ?
            """,
            (
                guild_id,
                user_id,
                limit
            )
        ) as cursor:

            return await cursor.fetchall()


# ======================================
# GET CASE
# ======================================

async def get_case(case_id: int):

    async with await get_db() as db:

        async with db.execute(
            """
            SELECT *
            FROM logs_data
            WHERE case_id=?
            """,
            (case_id,)
        ) as cursor:

            return await cursor.fetchone()


# ======================================
# DELETE CASE
# ======================================

async def delete_case(case_id: int):

    async with await get_db() as db:

        await db.execute(
            """
            DELETE FROM logs_data
            WHERE case_id=?
            """,
            (case_id,)
        )

        await db.commit()


# ======================================
# EMBEDS
# ======================================

def build_case_embed(case_data):

    if not case_data:
        return None

    content = case_data["content"] or "No details."

    if len(content) > 1000:

        content = content[:997] + "..."

    embed = discord.Embed(

        title=f"Case #{case_data['case_id']}",

        description=(
            f"Action: "
            f"**{case_data['type'].upper()}**"
        ),

        color=BRAND_COLOR

    )

    embed.add_field(

        name="User",

        value=(
            f"<@{case_data['user_id']}>\n"
            f"`{case_data['user_id']}`"
        ),

        inline=True

    )

    if case_data["moderator_id"]:

        embed.add_field(

            name="Moderator",

            value=(
                f"<@{case_data['moderator_id']}>\n"
                f"`{case_data['moderator_id']}`"
            ),

            inline=True

        )

    embed.add_field(

        name="Details",

        value=content,

        inline=False

    )

    embed.set_footer(

        text=str(case_data["timestamp"])

    )

    return embed


def quick_embed(
    title: str,
    description: str,
    color=BRAND_COLOR
):

    return discord.Embed(

        title=title,

        description=description,

        color=color

    )
