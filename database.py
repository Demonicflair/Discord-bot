import aiosqlite
import os

# For Railway, this path works best. 
# Ensure you have a Railway Volume mounted to "bot.db" if you want data to persist.
DB_PATH = "bot.db"

async def initialize_db():
    """Initializes the database and creates tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable WAL mode for high performance (allows concurrent reads/writes)
        await db.execute("PRAGMA journal_mode=WAL")
        
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
        
        # Whitelist Table (Used for Anti-Nuke/Security)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER, 
                guild_id INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        
        await db.commit()
    print("✅ Database initialized and optimized.")

async def add_xp(u, g, amt):
    """Adds XP and handles leveling logic."""
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
        # Advanced math: Leveling gets harder as you go (Level * 150)
        xp_needed = level * 150 
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

async def get_lb(g):
    """Returns the top 10 users in a specific guild."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, level FROM levels WHERE guild_id=? ORDER BY level DESC LIMIT 10",
            (g,)
        ) as cursor:
            return await cursor.fetchall()

async def add_warn(u, g):
    """Increments the warning count for a user."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT count FROM warnings WHERE user_id=? AND guild_id=?", (u, g)
        ) as cursor:
            d = await cursor.fetchone()
            
        count = (d[0] + 1) if d else 1

        await db.execute(
            "INSERT OR REPLACE INTO warnings (user_id, guild_id, count) VALUES (?, ?, ?)",
            (u, g, count)
        )
        await db.commit()
        return count

async def add_whitelist(u, g):
    """Adds a user to the security whitelist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO whitelist VALUES (?, ?)", (u, g))
        await db.commit()

async def is_whitelisted(u, g):
    """Checks if a user is whitelisted."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM whitelist WHERE user_id=? AND guild_id=?", (u, g)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None
            
