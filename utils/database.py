import os
import aiosqlite

from utils.config import DB_PATH


# ==================================================
# DATABASE FOLDER
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


async def close_db(db):

    if db:
        await db.close()


# ==================================================
# TABLES
# ==================================================

TABLES = [

"""
CREATE TABLE IF NOT EXISTS settings(
guild_id INTEGER,
feature TEXT,
enabled INTEGER DEFAULT 1,
PRIMARY KEY(guild_id,feature)
)
""",

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

"""
CREATE TABLE IF NOT EXISTS automod_settings(
guild_id INTEGER,
feature TEXT,
enabled INTEGER,
limit_value INTEGER,
punishment TEXT,
PRIMARY KEY(guild_id,feature)
)
""",

"""
CREATE TABLE IF NOT EXISTS automod_whitelist(
guild_id INTEGER,
user_id INTEGER,
PRIMARY KEY(guild_id,user_id)
)
""",

"""
CREATE TABLE IF NOT EXISTS automod_warns(
guild_id INTEGER,
user_id INTEGER,
warns INTEGER DEFAULT 0,
PRIMARY KEY(guild_id,user_id)
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

# FIXED GIVEAWAYS TABLE

"""
CREATE TABLE IF NOT EXISTS giveaways(

message_id INTEGER PRIMARY KEY,

guild_id INTEGER,

channel_id INTEGER,

prize TEXT,

winners INTEGER,

end_time INTEGER,

ended INTEGER DEFAULT 0,

req_role INTEGER,

black_role INTEGER

)
""",

"""
CREATE TABLE IF NOT EXISTS giveaway_entries(

message_id INTEGER,

user_id INTEGER,

PRIMARY KEY(
message_id,
user_id
)

)
""",

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
PRIMARY KEY(guild_id,channel_id)
)
""",

"""
CREATE TABLE IF NOT EXISTS xp_boosts(
guild_id INTEGER,
role_id INTEGER,
multiplier REAL DEFAULT 1,
PRIMARY KEY(guild_id,role_id)
)
""",

"""
CREATE TABLE IF NOT EXISTS reaction_roles(
guild_id INTEGER,
role_id INTEGER,
emoji TEXT,
PRIMARY KEY(guild_id,role_id)
)
""",

"""
CREATE TABLE IF NOT EXISTS afk(
user_id INTEGER,
guild_id INTEGER,
reason TEXT,
since INTEGER,
PRIMARY KEY(user_id,guild_id)
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
""",

"""
CREATE INDEX IF NOT EXISTS idx_giveaway_entries
ON giveaway_entries(message_id)
"""

]


# ==================================================
# INITIALIZE DATABASE
# ==================================================

async def initialize_db():

    db = await get_db()

    try:

        for table in TABLES:

            await db.execute(
                table
            )

        for index in INDEXES:

            await db.execute(
                index
            )

        await db.commit()

    finally:

        await close_db(db)
