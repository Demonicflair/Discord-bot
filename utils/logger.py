import aiosqlite
import discord
import datetime

DB_PATH = "logs.db"

# Cache to prevent database spamming for every message/event
_settings_cache = {}

async def init_db():
    """Initialize the database with optimized settings."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable WAL mode for faster concurrent reading/writing
        await db.execute("PRAGMA journal_mode=WAL")
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS log_channels(
            guild_id INTEGER PRIMARY KEY,
            mod_log INTEGER,
            bot_log INTEGER
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS log_settings(
            guild_id INTEGER,
            log_type TEXT,
            enabled INTEGER,
            PRIMARY KEY (guild_id, log_type)
        )
        """)

        await db.execute("""
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
        await db.commit()

# =========================
# ASYNC FETCHING & SETTING
# =========================

async def get_logs(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT mod_log, bot_log FROM log_channels WHERE guild_id=?", (guild_id,)) as cur:
            return await cur.fetchone()

async def set_log_channel(guild_id, mod_log=None, bot_log=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO log_channels (guild_id, mod_log, bot_log) VALUES (?, ?, ?)",
            (guild_id, mod_log, bot_log)
        )
        await db.commit()

async def save_log(guild_id, user_id, log_type, content, moderator_id=0):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO logs_data (guild_id, user_id, moderator_id, type, content) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, moderator_id, log_type, content)
        )
        await db.commit()
        return cursor.lastrowid

# =========================
# SMART SETTINGS (WITH CACHE)
# =========================

async def is_log_enabled(guild_id, log_type):
    """Checks cache first, then DB, for maximum performance."""
    cache_key = (guild_id, log_type)
    if cache_key in _settings_cache:
        return _settings_cache[cache_key]

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT enabled FROM log_settings WHERE guild_id=? AND log_type=?", (guild_id, log_type)) as cur:
            r = await cur.fetchone()
            state = r is None or r[0] == 1
            _settings_cache[cache_key] = state
            return state

async def set_log_state(guild_id, log_type, state):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO log_settings (guild_id, log_type, enabled) VALUES (?, ?, ?)",
            (guild_id, log_type, int(state))
        )
        await db.commit()
        # Update cache instantly
        _settings_cache[(guild_id, log_type)] = state

# =========================
# SEARCH & HISTORY
# =========================

async def get_user_history(guild_id, user_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM logs_data WHERE guild_id=? AND user_id=? ORDER BY timestamp DESC LIMIT ?",
            (guild_id, user_id, limit)
        ) as cur:
            return await cur.fetchall()

# =========================
# UI BUILDER
# =========================

def build_case_embed(case):
    if not case: return None
    
    c_id, g_id, u_id, m_id, l_type, content, stamp = case
    
    embed = discord.Embed(
        title=f"📁 Case #{c_id}",
        description=f"**Action:** {l_type.replace('_', ' ').title()}",
        color=0x2b2d31,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="👤 Target User", value=f"<@{u_id}>\n`ID: {u_id}`", inline=True)
    if m_id != 0:
        embed.add_field(name="🛠️ Moderator", value=f"<@{m_id}>\n`ID: {m_id}`", inline=True)
    
    embed.add_field(name="📝 Details", value=content or "No details provided.", inline=False)
    embed.set_footer(text=f"Dem Security System • {stamp}")
    return embed
