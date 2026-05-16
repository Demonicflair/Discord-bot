import aiosqlite

DB_PATH = "data.db"


# =========================
# DATABASE INITIALIZER
# =========================
async def initialize_db():

    async with aiosqlite.connect(DB_PATH) as db:

        # =========================
        # SQLITE OPTIMIZATION
        # =========================
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute("PRAGMA temp_store=MEMORY")

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
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            reason TEXT,
            moderator_id INTEGER,
            timestamp INTEGER
        )
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_warnings_user
        ON warnings(user_id, guild_id)
        """)

        # =========================
        # SECURITY SCORES
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
        # ANTINUKE WHITELIST
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS antinuke_whitelist (
            guild_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY(guild_id, user_id)
        )
        """)

        # =========================
        # TICKET BLACKLIST
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ticket_blacklist (
            guild_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY(guild_id, user_id)
        )
        """)

        # =========================
        # TICKET SETTINGS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ticket_settings (
            guild_id INTEGER PRIMARY KEY,
            category_id INTEGER,
            log_channel INTEGER,
            panel_channel INTEGER,
            support_role INTEGER
        )
        """)

        # =========================
        # TICKET COUNTER
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ticket_counter (
            guild_id INTEGER PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
        """)

        # =========================
        # ACTIVE TICKETS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS active_tickets (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            user_id INTEGER,
            created_at INTEGER
        )
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_active_tickets
        ON active_tickets(guild_id, user_id)
        """)

        # =========================
        # WELCOME SETTINGS
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
        # LOG HISTORY / CASES
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

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_user
        ON logs_data(guild_id, user_id)
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_logs_type
        ON logs_data(guild_id, type)
        """)

        # =========================
        # GIVEAWAYS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS giveaways (
            message_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            channel_id INTEGER,
            prize TEXT,
            winners INTEGER,
            ends_at INTEGER,
            hosted_by INTEGER
        )
        """)

        # =========================
        # LEVELING SYSTEM
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS levels (
            user_id INTEGER,
            guild_id INTEGER,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, guild_id)
        )
        """)

        await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_levels
        ON levels(guild_id, xp)
        """)

        # =========================
        # ECONOMY
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS economy (
            user_id INTEGER,
            guild_id INTEGER,
            balance INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, guild_id)
        )
        """)

        # =========================
        # REACTION ROLES
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reaction_roles (
            guild_id INTEGER,
            channel_id INTEGER,
            message_id INTEGER,
            role_id INTEGER,
            emoji TEXT,
            PRIMARY KEY(message_id, role_id, emoji)
        )
        """)

        # =========================
        # COMMAND COOLDOWNS
        # =========================
        await db.execute("""
        CREATE TABLE IF NOT EXISTS command_usage (
            guild_id INTEGER,
            user_id INTEGER,
            command_name TEXT,
            uses INTEGER DEFAULT 0,
            PRIMARY KEY(guild_id, user_id, command_name)
        )
        """)

        # =========================
        # FINAL SAVE
        # =========================
        await db.commit()


# =========================
# SAFE DATABASE CONNECTION
# =========================
async def get_db():

    db = await aiosqlite.connect(DB_PATH)

    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA synchronous=NORMAL")

    db.row_factory = aiosqlite.Row

    return db
