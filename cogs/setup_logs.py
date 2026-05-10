import discord
from discord.ext import commands
import asyncio
import aiosqlite

from utils.logger import DB_PATH, get_logs # Using the DB_PATH from our new logger

# =========================
# CONFIG
# =========================
MOD_LOG_NAME = "mod-logs"
BOT_LOG_NAME = "bot-logs"
LOG_CATEGORY_NAME = "SERVER LOGS"
DEM_COLOR = 0x2b2d31

# =========================
# EMBED HELPER
# =========================
def build_embed(title, description=None, color=DEM_COLOR):
    return discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )

class SetupLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # CREATE LOGS LOGIC
    # =========================
    async def create_logs(self, guild):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM log_channels WHERE guild_id=?", (guild.id,)) as cur:
                if await cur.fetchone():
                    return False # Already setup

        # Setup Permissions: Hide from everyone, show to Admin & Bot
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
        }

        # Auto-add Administrator roles to the view list
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # 1. Get or Create Category
        category = discord.utils.get(guild.categories, name=LOG_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(LOG_CATEGORY_NAME, overwrites=overwrites)

        # 2. Get or Create Channels
        mod_log = discord.utils.get(guild.text_channels, name=MOD_LOG_NAME)
        if not mod_log:
            mod_log = await guild.create_text_channel(MOD_LOG_NAME, category=category, topic="Dem | Moderation Actions")

        bot_log = discord.utils.get(guild.text_channels, name=BOT_LOG_NAME)
        if not bot_log:
            bot_log = await guild.create_text_channel(BOT_LOG_NAME, category=category, topic="Dem | System & Security Logs")

        # 3. Database Update
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO log_channels (guild_id, mod_log, bot_log) VALUES (?, ?, ?)",
                           (guild_id, mod_log.id, bot_log.id))
            await db.commit()
        
        return True

    # =========================
    # LISTENERS
    # =========================
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.create_logs(guild)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not isinstance(channel, discord.TextChannel): return

        logs = await get_logs(channel.guild.id)
        if not logs: return

        mod_id, bot_id = logs
        if channel.id not in [mod_id, bot_id]: return

        # Self-Healing: Recreate the deleted channel
        await asyncio.sleep(2) # Prevent rate limits
        new_ch = await channel.guild.create_text_channel(
            channel.name, 
            category=channel.category,
            topic="Dem | Auto-Restored Log Channel"
        )

        field = "mod_log" if channel.id == mod_id else "bot_log"
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(f"UPDATE log_channels SET {field}=? WHERE guild_id=?", (new_ch.id, channel.guild.id))
            await db.commit()
        
        await new_ch.send(embed=build_embed("♻️ Channel Restored", f"The `{channel.name}` was deleted and has been automatically recreated.", discord.Color.orange()))

    # =========================
    # HYBRID COMMANDS
    # =========================
    @commands.hybrid_command(name="setuplogs", description="Automatically configure Dem's logging system.")
    @commands.has_permissions(administrator=True)
    async def setuplogs(self, ctx):
        success = await self.create_logs(ctx.guild)
        if success:
            await ctx.send(embed=build_embed("✅ Setup Complete", "Created log category and channels successfully."))
        else:
            await ctx.send(embed=build_embed("⚠️ Already Setup", "Logging channels already exist in the database. Use `!resetlogs` if you want to rebuild them.", discord.Color.gold()))

    @commands.hybrid_command(name="resetlogs", description="Delete current log settings and recreate them.")
    @commands.has_permissions(administrator=True)
    async def resetlogs(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM log_channels WHERE guild_id=?", (ctx.guild.id,))
            await db.commit()
        
        await self.create_logs(ctx.guild)
        await ctx.send(embed=build_embed("♻️ System Reset", "All log channel mappings have been cleared and recreated."))

async def setup(bot):
    await bot.add_cog(SetupLogs(bot))
