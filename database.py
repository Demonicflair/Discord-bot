import aiosqlite
import os

# For Railway, it's best to use a path that matches your Volume mount
DB_PATH = "bot.db"

async def initialize_db():
    """Call this in your main.py on_ready to ensure tables exist"""
    async with aiosqlite.connect(DB_PATH) as db:
        # We use 'REPLACE' logic for easier updates later
        await db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                user_id INTEGER, guild_id INTEGER, xp INTEGER, level INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER, guild_id INTEGER, count INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER, guild_id INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.commit()

async def add_xp(u, g, amt):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT xp, level FROM levels WHERE user_id=? AND guild_id=?", (u, g)) as cursor:
            d = await cursor.fetchone()
        
        if not d:
            xp, level = amt, 1
        else:
            xp, level = d[0] + amt, d[1]

        leveled = False
        # Advanced math: higher levels require more XP (Current Level * 150)
        xp_needed = level * 150 
        if xp >= xp_needed:
            xp = 0
            level += 1
            leveled = True

        await db.execute("INSERT OR REPLACE INTO levels (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)", (u, g, xp, level))
        await db.commit()
        return level, leveled

async def is_whitelisted(u, g):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM whitelist WHERE user_id=? AND guild_id=?", (u, g)) as cursor:
            result = await cursor.fetchone()
            return result is not None
