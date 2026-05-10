import aiosqlite
import asyncio

DB_PATH = "data.db"

async def initialize_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Features & Settings
        await db.execute("""CREATE TABLE IF NOT EXISTS settings 
            (guild_id INTEGER, feature TEXT, enabled INTEGER, PRIMARY KEY(guild_id, feature))""")
        
        # Moderation & Security
        await db.execute("""CREATE TABLE IF NOT EXISTS warnings 
            (user_id INTEGER, guild_id INTEGER, reason TEXT, moderator_id INTEGER, timestamp INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS security_scores 
            (user_id INTEGER, guild_id INTEGER, score INTEGER, PRIMARY KEY(user_id, guild_id))""")
        
        # Tickets & Welcome
        await db.execute("""CREATE TABLE IF NOT EXISTS ticket_blacklist 
            (guild_id INTEGER, user_id INTEGER, PRIMARY KEY(guild_id, user_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS welcome_settings (
            guild_id INTEGER PRIMARY KEY, welcome_channel INTEGER, leave_channel INTEGER,
            welcome_message TEXT, leave_message TEXT, autorole INTEGER, use_embed INTEGER)""")
        
        # Utility & AFK
        await db.execute("""CREATE TABLE IF NOT EXISTS afk 
            (user_id INTEGER, guild_id INTEGER, reason TEXT, since INTEGER, PRIMARY KEY(user_id, guild_id))""")
        
        await db.commit()

async def get_db_connection():
    return await aiosqlite.connect(DB_PATH)
  
