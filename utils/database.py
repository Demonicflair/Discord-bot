import os
import aiosqlite

# ==================================================
# PATHS
# ==================================================

DB_FOLDER = "database"

os.makedirs(
    DB_FOLDER,
    exist_ok=True
)

DB_PATH = os.path.join(
    DB_FOLDER,
    "dem.db"
)

_CONNECTION_TIMEOUT = 30


# ==================================================
# SQLITE CONFIG
# ==================================================

async def configure_db(
    db: aiosqlite.Connection
):

    await db.execute(
        "PRAGMA journal_mode=WAL"
    )

    await db.execute(
        "PRAGMA synchronous=NORMAL"
    )

    await db.execute(
        "PRAGMA foreign_keys=ON"
    )

    await db.execute(
        "PRAGMA temp_store=MEMORY"
    )

    await db.execute(
        "PRAGMA cache_size=-5000"
    )

    await db.execute(
        "PRAGMA busy_timeout=30000"
    )

    db.row_factory = (
        aiosqlite.Row
    )


# ==================================================
# DATABASE CONNECTION
# ==================================================

async def get_db():

    db = await aiosqlite.connect(

        DB_PATH,

        timeout=_CONNECTION_TIMEOUT

    )

    await configure_db(
        db
    )

    return db


async def close_db(db):

    if db:

        await db.close()


# ==================================================
# TABLE CREATION
# ==================================================

TABLES = [

"""
CREATE TABLE IF NOT EXISTS settings(

guild_id INTEGER,
feature TEXT,
enabled INTEGER DEFAULT 1,

PRIMARY KEY(
guild_id,
feature
)

)
""",

"""
CREATE TABLE IF NOT EXISTS warnings(

id INTEGER PRIMARY KEY AUTOINCREMENT,

user_id INTEGER NOT NULL,

guild_id INTEGER NOT NULL,

reason TEXT,

moderator_id INTEGER,

timestamp INTEGER

)
""",

"""
CREATE TABLE IF NOT EXISTS log_channels(

guild_id INTEGER PRIMARY KEY,

mod_log INTEGER,

bot_log INTEGER

)
""",

"""
CREATE TABLE IF NOT EXISTS log_settings(

guild_id INTEGER,

log_type TEXT,

enabled INTEGER DEFAULT 1,

PRIMARY KEY(
guild_id,
log_type
)

)
""",

"""
CREATE TABLE IF NOT EXISTS logs_data(

case_id INTEGER PRIMARY KEY AUTOINCREMENT,

guild_id INTEGER,

user_id INTEGER,

moderator_id INTEGER,

type TEXT,

content TEXT,

timestamp DATETIME DEFAULT CURRENT_TIMESTAMP

)
""",

"""
CREATE TABLE IF NOT EXISTS automod_settings(

guild_id INTEGER,

feature TEXT,

enabled INTEGER,

limit_value INTEGER,

punishment TEXT,

PRIMARY KEY(
guild_id,
feature
)

)
""",

"""
CREATE TABLE IF NOT EXISTS automod_whitelist(

guild_id INTEGER,

user_id INTEGER,

PRIMARY KEY(
guild_id,
user_id
)

)
""",

"""
CREATE TABLE IF NOT EXISTS automod_warns(

guild_id INTEGER,

user_id INTEGER,

warns INTEGER DEFAULT 0,

PRIMARY KEY(
guild_id,
user_id
)

)
""",

"""
CREATE TABLE IF NOT EXISTS verification(

guild_id INTEGER PRIMARY KEY,

role_id INTEGER,

channel_id INTEGER

)
""",

"""
CREATE TABLE IF NOT EXISTS ticket_settings(

guild_id INTEGER PRIMARY KEY,

category_id INTEGER,

log_channel INTEGER,

panel_channel INTEGER,

support_role INTEGER

)
""",

"""
CREATE TABLE IF NOT EXISTS active_tickets(

channel_id INTEGER PRIMARY KEY,

guild_id INTEGER,

user_id INTEGER,

created_at INTEGER

)
""",

"""
CREATE TABLE IF NOT EXISTS giveaways(

message_id INTEGER PRIMARY KEY,

guild_id INTEGER,

channel_id INTEGER,

prize TEXT,

winners INTEGER,

ends_at INTEGER,

hosted_by INTEGER

)
""",

"""
CREATE TABLE IF NOT EXISTS levels(

user_id INTEGER,

guild_id INTEGER,

xp INTEGER DEFAULT 0,

level INTEGER DEFAULT 0,

PRIMARY KEY(
user_id,
guild_id
)

)
""",

# reaction roles (needed because we fixed utils/reactionroles.py)

"""
CREATE TABLE IF NOT EXISTS reaction_roles(

guild_id INTEGER,

role_id INTEGER,

emoji TEXT,

PRIMARY KEY(
guild_id,
role_id
)

)
"""

]

INDEXES = [

"""
CREATE INDEX IF NOT EXISTS idx_warns
ON warnings(
guild_id,
user_id
)
""",

"""
CREATE INDEX IF NOT EXISTS idx_logs
ON logs_data(
guild_id,
user_id
)
""",

"""
CREATE INDEX IF NOT EXISTS idx_levels
ON levels(
guild_id,
user_id
)
"""

]


# ==================================================
# INITIALIZE DATABASE
# ==================================================

async def initialize_db():

    async with await get_db() as db:

        for table in TABLES:

            await db.execute(
                table
            )

        for index in INDEXES:

            await db.execute(
                index
            )

        await db.commit()
