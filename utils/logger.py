import discord
import aiosqlite

DB_PATH = "data.db"

_settings_cache = {}


# =========================
# GET LOG CHANNELS
# =========================
async def get_logs(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT mod_log, bot_log FROM log_channels WHERE guild_id=?",
            (guild_id,)
        ) as cursor:
            return await cursor.fetchone()


# =========================
# SAVE CASE LOG
# =========================
async def save_log(guild_id, user_id, log_type, content, moderator_id=0):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO logs_data
            (guild_id, user_id, moderator_id, type, content)
            VALUES (?, ?, ?, ?, ?)
        """, (
            guild_id,
            user_id,
            moderator_id,
            log_type,
            content
        ))

        await db.commit()
        return cursor.lastrowid


# =========================
# LOG ENABLE CHECK
# =========================
async def is_log_enabled(guild_id, log_type):
    key = (guild_id, log_type)

    if key in _settings_cache:
        return _settings_cache[key]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT enabled FROM log_settings
            WHERE guild_id=? AND log_type=?
        """, (guild_id, log_type)) as cursor:

            data = await cursor.fetchone()

            enabled = True if data is None else bool(data[0])

            _settings_cache[key] = enabled
            return enabled


# =========================
# CHANGE LOG STATE
# =========================
async def set_log_state(guild_id, log_type, state):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO log_settings
            (guild_id, log_type, enabled)
            VALUES (?, ?, ?)
        """, (
            guild_id,
            log_type,
            int(state)
        ))

        await db.commit()

    _settings_cache[(guild_id, log_type)] = state


# =========================
# USER HISTORY
# =========================
async def get_user_history(guild_id, user_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT * FROM logs_data
            WHERE guild_id=? AND user_id=?
            ORDER BY case_id DESC
            LIMIT ?
        """, (
            guild_id,
            user_id,
            limit
        )) as cursor:

            return await cursor.fetchall()


# =========================
# EMBED BUILDER
# =========================
def build_case_embed(case_data):

    if not case_data:
        return None

    case_id, guild_id, user_id, moderator_id, log_type, content, timestamp = case_data

    embed = discord.Embed(
        title=f"📁 Case #{case_id}",
        color=0x2b2d31
    )

    embed.add_field(
        name="Action",
        value=log_type.title(),
        inline=True
    )

    embed.add_field(
        name="User",
        value=f"<@{user_id}> (`{user_id}`)",
        inline=True
    )

    if moderator_id:
        embed.add_field(
            name="Moderator",
            value=f"<@{moderator_id}> (`{moderator_id}`)",
            inline=True
        )

    embed.add_field(
        name="Details",
        value=content[:1024],
        inline=False
    )

    embed.set_footer(text=f"Dem Logging System • {timestamp}")

    return embed
