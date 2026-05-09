import aiosqlite
import os

# For Railway, this path works best. 
DB_PATH = "bot.db"

async def initialize_db():
    """Initializes the database with high-performance settings."""
    async with aiosqlite.connect(DB_PATH) as db:
        # WAL mode prevents 'database is locked' errors during heavy use
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        
        # Levels Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                user_id INTEGER, 
                guild_id INTEGER, 
                xp INTEGER, 
                level INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        # Warnings Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER, 
                guild_id INTEGER, 
                count INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        # Whitelist Table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER, 
                guild_id INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        await db.commit()
    print("✨ Database optimized for high traffic.")

# =========================
# NEW & UPGRADED COMMANDS
# =========================

async def add_xp(u, g, amt):
    """Adds XP with a smoother leveling curve."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT xp, level FROM levels WHERE user_id=? AND guild_id=?", (u, g)
        ) as cursor:
            d = await cursor.fetchone()
        
        if not d:
            xp, level = amt, 1
        else:
            xp, level = d[0] + amt, d[1]

        leveled = False
        # Famous bots use a dynamic curve: level * level * 100
        xp_needed = (level ** 2) * 100 
        if xp >= xp_needed:
            xp = 0
            level += 1
            leveled = True

        await db.execute(
            "INSERT OR REPLACE INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
            (u, g, xp, level)
        )
        await db.commit()
        return level, leveled

async def get_user_stats(u, g):
    """New: Quick fetch for a user's full profile."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT xp, level FROM levels WHERE user_id=? AND guild_id=?", (u, g)
        ) as cursor:
            return await cursor.fetchone()

async def remove_whitelist(u, g):
    """New: Easily remove a user from security whitelist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM whitelist WHERE user_id=? AND guild_id=?", (u, g))
        await db.commit()

async def is_whitelisted(u, g):
    """Checks if a user is whitelisted."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM whitelist WHERE user_id=? AND guild_id=?", (u, g)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None
