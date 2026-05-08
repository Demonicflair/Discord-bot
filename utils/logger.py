import sqlite3
import discord

# =========================
# DATABASE
# =========================
db = sqlite3.connect(
    "logs.db",
    check_same_thread=False
)

cursor = db.cursor()

# =========================
# TABLES
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS log_channels(
    guild_id INTEGER PRIMARY KEY,
    mod_log INTEGER,
    bot_log INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS log_settings(
    guild_id INTEGER,
    log_type TEXT,
    enabled INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs_data(
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    type TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()

# =========================
# FETCH LOG CHANNELS
# =========================
def get_logs(guild_id):

    cursor.execute(
        "SELECT mod_log, bot_log FROM log_channels WHERE guild_id=?",
        (guild_id,)
    )

    return cursor.fetchone()

# =========================
# SET LOG CHANNELS
# =========================
def set_log_channel(guild_id, mod_log=None, bot_log=None):

    cursor.execute(
        "DELETE FROM log_channels WHERE guild_id=?",
        (guild_id,)
    )

    cursor.execute(
        """
        INSERT INTO log_channels(
            guild_id,
            mod_log,
            bot_log
        )
        VALUES (?, ?, ?)
        """,
        (
            guild_id,
            mod_log,
            bot_log
        )
    )

    db.commit()

# =========================
# SAVE LOG
# =========================
def save_log(
    guild_id,
    user_id,
    log_type,
    content,
    moderator_id=0
):

    cursor.execute(
        """
        INSERT INTO logs_data(
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

    db.commit()

    return cursor.lastrowid

# =========================
# GET CASE
# =========================
def get_case(case_id):

    cursor.execute(
        """
        SELECT *
        FROM logs_data
        WHERE case_id=?
        """,
        (case_id,)
    )

    return cursor.fetchone()

# =========================
# USER HISTORY
# =========================
def get_user_history(guild_id, user_id, limit=10):

    cursor.execute(
        """
        SELECT *
        FROM logs_data
        WHERE guild_id=?
        AND user_id=?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (
            guild_id,
            user_id,
            limit
        )
    )

    return cursor.fetchall()

# =========================
# SEARCH LOGS
# =========================
def search_logs_db(
    guild_id,
    query,
    log_type=None
):

    if log_type:

        cursor.execute(
            """
            SELECT *
            FROM logs_data
            WHERE guild_id=?
            AND type=?
            AND content LIKE ?
            ORDER BY timestamp DESC
            LIMIT 15
            """,
            (
                guild_id,
                log_type,
                f"%{query}%"
            )
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM logs_data
            WHERE guild_id=?
            AND content LIKE ?
            ORDER BY timestamp DESC
            LIMIT 15
            """,
            (
                guild_id,
                f"%{query}%"
            )
        )

    return cursor.fetchall()

# =========================
# RECENT LOGS
# =========================
def get_recent_logs(
    guild_id,
    limit=10
):

    cursor.execute(
        """
        SELECT *
        FROM logs_data
        WHERE guild_id=?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (
            guild_id,
            limit
        )
    )

    return cursor.fetchall()

# =========================
# DELETE CASE
# =========================
def delete_case(case_id):

    cursor.execute(
        """
        DELETE FROM logs_data
        WHERE case_id=?
        """,
        (case_id,)
    )

    db.commit()

# =========================
# LOG FILTERS
# =========================
def is_log_enabled(
    guild_id,
    log_type
):

    cursor.execute(
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

    r = cursor.fetchone()

    return r is None or r[0] == 1

# =========================
# ENABLE / DISABLE LOGS
# =========================
def set_log(
    guild_id,
    log_type,
    state
):

    cursor.execute(
        """
        DELETE FROM log_settings
        WHERE guild_id=?
        AND log_type=?
        """,
        (
            guild_id,
            log_type
        )
    )

    cursor.execute(
        """
        INSERT INTO log_settings
        VALUES (?, ?, ?)
        """,
        (
            guild_id,
            log_type,
            int(state)
        )
    )

    db.commit()

# =========================
# BUILD LOG EMBED
# =========================
def build_case_embed(case):

    if not case:
        return None

    (
        case_id,
        guild_id,
        user_id,
        moderator_id,
        log_type,
        content,
        timestamp
    ) = case

    embed = discord.Embed(
        title=f"📁 Case #{case_id}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📌 Type",
        value=log_type,
        inline=True
    )

    embed.add_field(
        name="👤 User ID",
        value=user_id,
        inline=True
    )

    embed.add_field(
        name="🛠️ Moderator ID",
        value=moderator_id,
        inline=True
    )

    embed.add_field(
        name="📝 Details",
        value=content,
        inline=False
    )

    embed.set_footer(
        text=f"Timestamp: {timestamp}"
    )

    return embed
