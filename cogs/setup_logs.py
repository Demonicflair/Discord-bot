import discord
from discord.ext import commands
import asyncio
import aiosqlite

from utils.logger import DB_PATH, get_logs
from utils.config import (
    MOD_LOG_NAME,
    BOT_LOG_NAME,
    LOG_CATEGORY_NAME
)

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


# =========================
# SETUP LOGS COG
# =========================
class SetupLogs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # CREATE LOG SYSTEM
    # =========================
    async def create_logs(self, guild):

        # =========================
        # CHECK EXISTING SETUP
        # =========================
        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                "SELECT mod_log, bot_log FROM log_channels WHERE guild_id=?",
                (guild.id,)
            ) as cursor:

                existing = await cursor.fetchone()

        # =========================
        # PERMISSIONS
        # =========================
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True
            )
        }

        # Add Admin Roles
        for role in guild.roles:

            if role.permissions.administrator:

                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        # =========================
        # CATEGORY
        # =========================
        category = discord.utils.get(
            guild.categories,
            name=LOG_CATEGORY_NAME
        )

        if not category:

            try:
                category = await guild.create_category(
                    LOG_CATEGORY_NAME,
                    overwrites=overwrites,
                    reason="Dem Logging System Setup"
                )

            except discord.Forbidden:
                return False

        # =========================
        # MOD LOG CHANNEL
        # =========================
        mod_log = discord.utils.get(
            guild.text_channels,
            name=MOD_LOG_NAME
        )

        if not mod_log:

            try:
                mod_log = await guild.create_text_channel(
                    MOD_LOG_NAME,
                    category=category,
                    topic="Dem | Moderation Logs"
                )

            except discord.Forbidden:
                return False

        # =========================
        # BOT LOG CHANNEL
        # =========================
        bot_log = discord.utils.get(
            guild.text_channels,
            name=BOT_LOG_NAME
        )

        if not bot_log:

            try:
                bot_log = await guild.create_text_channel(
                    BOT_LOG_NAME,
                    category=category,
                    topic="Dem | Security & System Logs"
                )

            except discord.Forbidden:
                return False

        # =========================
        # SAVE TO DATABASE
        # =========================
        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                INSERT OR REPLACE INTO log_channels
                (guild_id, mod_log, bot_log)
                VALUES (?, ?, ?)
            """, (
                guild.id,
                mod_log.id,
                bot_log.id
            ))

            await db.commit()

        # =========================
        # SEND READY MESSAGE
        # =========================
        try:
            await mod_log.send(
                embed=build_embed(
                    "🛡️ Moderation Logs Ready",
                    "This channel will now track moderation actions."
                )
            )

            await bot_log.send(
                embed=build_embed(
                    "🤖 System Logs Ready",
                    "This channel will now track security and bot events."
                )
            )

        except:
            pass

        return True

    # =========================
    # AUTO SETUP ON JOIN
    # =========================
    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        await asyncio.sleep(3)

        try:
            await self.create_logs(guild)

        except Exception as e:
            print(f"[AUTO SETUP ERROR] {e}")

    # =========================
    # SELF HEALING
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        if not isinstance(channel, discord.TextChannel):
            return

        logs = await get_logs(channel.guild.id)

        if not logs:
            return

        mod_log_id, bot_log_id = logs

        if channel.id not in [mod_log_id, bot_log_id]:
            return

        await asyncio.sleep(2)

        try:

            new_channel = await channel.guild.create_text_channel(
                name=channel.name,
                category=channel.category,
                topic="Dem | Auto Restored Log Channel"
            )

        except discord.Forbidden:
            return

        field = (
            "mod_log"
            if channel.id == mod_log_id
            else "bot_log"
        )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                f"UPDATE log_channels SET {field}=? WHERE guild_id=?",
                (
                    new_channel.id,
                    channel.guild.id
                )
            )

            await db.commit()

        try:

            await new_channel.send(
                embed=build_embed(
                    "♻️ Channel Restored",
                    f"`{channel.name}` was deleted and automatically recreated.",
                    discord.Color.orange()
                )
            )

        except:
            pass

    # =========================
    # SETUP COMMAND
    # =========================
    @commands.hybrid_command(
        name="setuplogs",
        description="Setup Dem logging system."
    )
    @commands.has_permissions(administrator=True)
    async def setuplogs(self, ctx):

        success = await self.create_logs(ctx.guild)

        if success:

            await ctx.send(
                embed=build_embed(
                    "✅ Logging Setup Complete",
                    "Mod logs and bot logs are now configured."
                )
            )

        else:

            await ctx.send(
                embed=build_embed(
                    "❌ Setup Failed",
                    "I need Manage Channels permission.",
                    discord.Color.red()
                )
            )

    # =========================
    # RESET LOGS
    # =========================
    @commands.hybrid_command(
        name="resetlogs",
        description="Reset and rebuild log channels."
    )
    @commands.has_permissions(administrator=True)
    async def resetlogs(self, ctx):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                "DELETE FROM log_channels WHERE guild_id=?",
                (ctx.guild.id,)
            )

            await db.commit()

        success = await self.create_logs(ctx.guild)

        if success:

            await ctx.send(
                embed=build_embed(
                    "♻️ Logging System Reset",
                    "Log channels were recreated successfully."
                )
            )

        else:

            await ctx.send(
                embed=build_embed(
                    "❌ Reset Failed",
                    "I couldn't recreate the channels.",
                    discord.Color.red()
                )
            )


# =========================
# LOAD COG
# =========================
async def setup(bot):

    await bot.add_cog(SetupLogs(bot))
