import aiosqlite

DB_PATH = "data.db"


async def initialize_db():
    async with aiosqlite.connect(DB_PATH) as db:

        # Better SQLite performance
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")

        # =========================
        # SETTINGS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            guild_id INTEGER,
            feature TEXT,
            enabled INTEGER DEFAULT 1,
            PRIMARY KEY(guild_id, feature)
        )
        """)

        # =========================
        # WARNINGS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            guild_id INTEGER,
            reason TEXT,
            moderator_id INTEGER,
            timestamp INTEGER
        )
        """)

        # =========================
        # SECURITY
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS security_scores (
            user_id INTEGER,
            guild_id INTEGER,
            score INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, guild_id)
        )
        """)

        # =========================
        # TICKETS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ticket_blacklist (
            guild_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY(guild_id, user_id)
        )
        """)

        # =========================
        # WELCOME SYSTEM
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS welcome_settings (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel INTEGER,
            leave_channel INTEGER,
            welcome_message TEXT,
            leave_message TEXT,
            autorole INTEGER,
            use_embed INTEGER DEFAULT 1
        )
        """)

        # =========================
        # AFK SYSTEM
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS afk (
            user_id INTEGER,
            guild_id INTEGER,
            reason TEXT,
            since INTEGER,
            PRIMARY KEY(user_id, guild_id)
        )
        """)

        # =========================
        # LOG CHANNELS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS log_channels (
            guild_id INTEGER PRIMARY KEY,
            mod_log INTEGER,
            bot_log INTEGER
        )
        """)

        # =========================
        # LOG SETTINGS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS log_settings (
            guild_id INTEGER,
            log_type TEXT,
            enabled INTEGER DEFAULT 1,
            PRIMARY KEY(guild_id, log_type)
        )
        """)

        # =========================
        # LOG HISTORY
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS logs_data (
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


async def get_db():
    return await aiosqlite.connect(DB_PATH)
