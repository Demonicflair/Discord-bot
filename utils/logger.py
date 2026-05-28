import discord

from utils.database import get_db
from utils.config import BRAND_COLOR

# =========================
# CACHE
# =========================

_settings_cache = {}


# =========================
# GET LOG CHANNELS
# =========================

async def get_logs(guild_id: int):

    async with await get_db() as db:

        cursor = await db.execute(
            """
            SELECT mod_log, bot_log
            FROM log_channels
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

        data = await cursor.fetchone()

        await cursor.close()

        return data


# =========================
# SET LOG CHANNELS
# =========================

async def set_log_channels(
    guild_id: int,
    mod_log=None,
    bot_log=None
):

    old = await get_logs(guild_id)

    old_mod = old["mod_log"] if old else None
    old_bot = old["bot_log"] if old else None

    mod_log = old_mod if mod_log is None else mod_log
    bot_log = old_bot if bot_log is None else bot_log

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


# =========================
# SAVE LOG
# =========================

async def save_log(
    guild_id: int,
    user_id: int,
    log_type: str,
    content: str,
    moderator_id: int = 0
):

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
                log_type,
                content
            )
        )

        await db.commit()

        case_id = cursor.lastrowid

        await cursor.close()

        return case_id


# =========================
# SEND LOG
# =========================

async def send_log(
    guild,
    log_type: str,
    embed: discord.Embed
):

    logs = await get_logs(guild.id)

    if not logs:
        return

    mod_types = {
        "ban",
        "kick",
        "warn",
        "mute",
        "unmute",
        "clear"
    }

    channel_id = (

        logs["mod_log"]

        if log_type in mod_types

        else logs["bot_log"]

    )

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if not channel:
        return

    try:

        await channel.send(
            embed=embed
        )

    except discord.Forbidden:

        return

    except discord.HTTPException:

        return


# =========================
# LOG ENABLED
# =========================

async def is_log_enabled(
    guild_id: int,
    log_type: str
):

    key = (
        guild_id,
        log_type
    )

    if key in _settings_cache:

        return _settings_cache[key]

    async with await get_db() as db:

        cursor = await db.execute(
            """
            SELECT enabled
            FROM log_settings
            WHERE guild_id=?
            AND log_type=?
            """,
            (
                guild_id,
                log_type
            )
        )

        data = await cursor.fetchone()

        await cursor.close()

    enabled = (

        True

        if data is None

        else bool(data["enabled"])

    )

    _settings_cache[key] = enabled

    return enabled


# =========================
# SET LOG STATE
# =========================

async def set_log_state(
    guild_id: int,
    log_type: str,
    state: bool
):

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
                log_type,
                int(state)
            )
        )

        await db.commit()

    _settings_cache[
        (
            guild_id,
            log_type
        )
    ] = state


# =========================
# USER HISTORY
# =========================

async def get_user_history(
    guild_id: int,
    user_id: int,
    limit: int = 10
):

    async with await get_db() as db:

        cursor = await db.execute(
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
        )

        rows = await cursor.fetchall()

        await cursor.close()

        return rows


# =========================
# GET CASE
# =========================

async def get_case(
    case_id: int
):

    async with await get_db() as db:

        cursor = await db.execute(
            """
            SELECT *
            FROM logs_data
            WHERE case_id=?
            """,
            (case_id,)
        )

        row = await cursor.fetchone()

        await cursor.close()

        return row


# =========================
# DELETE CASE
# =========================

async def delete_case(
    case_id: int
):

    async with await get_db() as db:

        await db.execute(
            """
            DELETE FROM logs_data
            WHERE case_id=?
            """,
            (case_id,)
        )

        await db.commit()


# =========================
# EMBEDS
# =========================

def build_case_embed(
    case_data
):

    if not case_data:

        return None

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

    content = case_data["content"]

    embed.add_field(

        name="Details",

        value=(
            content[:1000] + "..."

            if len(content) > 1000

            else content
        ),

        inline=False
    )

    embed.set_footer(

        text=f"{case_data['timestamp']}"

    )

    return embed


def quick_embed(
    title,
    description,
    color=BRAND_COLOR
):

    return discord.Embed(

        title=title,

        description=description,

        color=color
    )
