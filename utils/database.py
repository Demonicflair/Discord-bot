# utils/database.py

import os
import aiosqlite

from utils.config import DB_PATH


# ==================================================
# CREATE DATABASE FOLDER
# ==================================================

db_folder = os.path.dirname(DB_PATH)

if db_folder:

    os.makedirs(
        db_folder,
        exist_ok=True
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
        "PRAGMA busy_timeout=30000"
    )

    await db.execute(
        "PRAGMA temp_store=MEMORY"
    )

    await db.execute(
        "PRAGMA cache_size=-5000"
    )

    db.row_factory = aiosqlite.Row


# ==================================================
# CONNECTION
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


# ==================================================
# TABLES
# ==================================================

TABLES = [

# SETTINGS

"""
CREATE TABLE IF NOT EXISTS settings(
guild_id INTEGER,
feature TEXT,
enabled INTEGER DEFAULT 1,
PRIMARY KEY(guild_id,feature)
)
""",

# WARNINGS

"""
CREATE TABLE IF NOT EXISTS warnings(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
guild_id INTEGER,
reason TEXT,
moderator_id INTEGER,
timestamp INTEGER
)
""",

# SECURITY

"""
CREATE TABLE IF NOT EXISTS security_scores(
guild_id INTEGER,
user_id INTEGER,
score INTEGER DEFAULT 0,
PRIMARY KEY(guild_id,user_id)
)
""",

"""
CREATE TABLE IF NOT EXISTS antinuke_whitelist(
guild_id INTEGER,
user_id INTEGER,
PRIMARY KEY(guild_id,user_id)
)
""",

# LOGGING

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
PRIMARY KEY(guild_id,log_type)
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

# TICKETS

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
CREATE TABLE IF NOT EXISTS ticket_blacklist(
guild_id INTEGER,
user_id INTEGER,
PRIMARY KEY(guild_id,user_id)
)
""",

"""
CREATE TABLE IF NOT EXISTS ticket_counter(
guild_id INTEGER PRIMARY KEY,
count INTEGER DEFAULT 0
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

# WELCOME

"""
CREATE TABLE IF NOT EXISTS welcome_settings(
guild_id INTEGER PRIMARY KEY,
welcome_channel INTEGER,
leave_channel INTEGER,
welcome_message TEXT,
leave_message TEXT,
autorole INTEGER,
use_embed INTEGER DEFAULT 1
)
""",

# GIVEAWAYS

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

# LEVELING (ADVANCED)

"""
CREATE TABLE IF NOT EXISTS levels(

guild_id INTEGER,
user_id INTEGER,

xp INTEGER DEFAULT 0,
level INTEGER DEFAULT 0,

prestige INTEGER DEFAULT 0,

messages INTEGER DEFAULT 0,

voice_seconds INTEGER DEFAULT 0,

weekly_xp INTEGER DEFAULT 0,

rep INTEGER DEFAULT 0,

bio TEXT DEFAULT '',

PRIMARY KEY(
guild_id,
user_id
)

)
""",

"""
CREATE TABLE IF NOT EXISTS level_settings(
guild_id INTEGER PRIMARY KEY,
enabled INTEGER DEFAULT 1,
levelup_channel INTEGER,
announce INTEGER DEFAULT 1
)
""",

"""
CREATE TABLE IF NOT EXISTS level_blacklist(
guild_id INTEGER,
channel_id INTEGER,
PRIMARY KEY(
guild_id,
channel_id
)
)
""",

"""
CREATE TABLE IF NOT EXISTS xp_boosts(
guild_id INTEGER,
role_id INTEGER,
multiplier REAL DEFAULT 1,
PRIMARY KEY(
guild_id,
role_id
)
)
""",

# AFK

"""
CREATE TABLE IF NOT EXISTS afk(
user_id INTEGER,
guild_id INTEGER,
reason TEXT,
since INTEGER,
PRIMARY KEY(
user_id,
guild_id
)
)
"""

]

# ==================================================
# INDEXES
# ==================================================

INDEXES = [

"""
CREATE INDEX IF NOT EXISTS idx_warns
ON warnings(guild_id,user_id)
""",

"""
CREATE INDEX IF NOT EXISTS idx_logs
ON logs_data(guild_id,user_id)
""",

"""
CREATE INDEX IF NOT EXISTS idx_levels
ON levels(guild_id,user_id)
"""

]


# ==================================================
# INIT DATABASE
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
