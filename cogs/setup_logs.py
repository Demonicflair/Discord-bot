# setup_logs.py

import discord
from discord.ext import commands
from discord import app_commands
import asyncio

from utils.logger import cursor, db, get_logs

# =========================
# CONFIG
# =========================
MOD_LOG_NAME = "mod-logs"
BOT_LOG_NAME = "bot-logs"
LOG_CATEGORY_NAME = "SERVER LOGS"


# =========================
# EMBED HELPER
# =========================
def embed_builder(title, description=None, color=discord.Color.blurple()):

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    return embed


# =========================
# SETUP LOGS COG
# =========================
class SetupLogs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # AUTO CREATE ON JOIN
    # =========================
    @commands.Cog.listener()
    async def on_guild_join(self, guild):

        try:
            await self.create_logs(guild)

        except Exception as e:
            print(f"[LOG SETUP ERROR] {guild.name} -> {e}")

    # =========================
    # CREATE LOGS
    # =========================
    async def create_logs(self, guild):

        existing = cursor.execute(
            "SELECT * FROM log_channels WHERE guild_id=?",
            (guild.id,)
        ).fetchone()

        if existing:
            return

        # =========================
        # PERMISSIONS
        # =========================
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            )
        }

        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True
            )

        # ADMIN ROLES
        for role in guild.roles:

            if role.permissions.administrator:

                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True
                )

        # =========================
        # CATEGORY
        # =========================
        category = discord.utils.get(
            guild.categories,
            name=LOG_CATEGORY_NAME
        )

        if category is None:

            category = await guild.create_category(
                LOG_CATEGORY_NAME,
                overwrites=overwrites,
                reason="Automatic log setup"
            )

        # =========================
        # CHANNELS
        # =========================
        mod_log = discord.utils.get(
            guild.text_channels,
            name=MOD_LOG_NAME
        )

        if mod_log is None:

            mod_log = await guild.create_text_channel(
                MOD_LOG_NAME,
                category=category,
                overwrites=overwrites,
                topic="Moderation logs",
                reason="Automatic log setup"
            )

        bot_log = discord.utils.get(
            guild.text_channels,
            name=BOT_LOG_NAME
        )

        if bot_log is None:

            bot_log = await guild.create_text_channel(
                BOT_LOG_NAME,
                category=category,
                overwrites=overwrites,
                topic="Bot logs",
                reason="Automatic log setup"
            )

        # =========================
        # DATABASE
        # =========================
        cursor.execute(
            "DELETE FROM log_channels WHERE guild_id=?",
            (guild.id,)
        )

        cursor.execute(
            "INSERT INTO log_channels VALUES (?, ?, ?)",
            (
                guild.id,
                mod_log.id,
                bot_log.id
            )
        )

        db.commit()

        # =========================
        # SEND STARTUP MESSAGE
        # =========================
        embed = embed_builder(
            "📄 Logging System Ready",
            (
                "This server now has:\n\n"
                f"• {mod_log.mention} → moderation logs\n"
                f"• {bot_log.mention} → bot/system logs"
            ),
            discord.Color.green()
        )

        await mod_log.send(embed=embed)

    # =========================
    # RECREATE DELETED LOGS
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        if not isinstance(channel, discord.TextChannel):
            return

        logs = get_logs(channel.guild.id)

        if not logs:
            return

        mod_log_id, bot_log_id = logs

        # =========================
        # MOD LOG RECREATE
        # =========================
        if channel.id == mod_log_id:

            await asyncio.sleep(1)

            new_channel = await channel.guild.create_text_channel(
                MOD_LOG_NAME,
                reason="Recreated deleted mod log"
            )

            cursor.execute(
                "UPDATE log_channels SET mod_log=? WHERE guild_id=?",
                (new_channel.id, channel.guild.id)
            )

            db.commit()

            embed = embed_builder(
                "♻️ Mod Log Recreated",
                "The moderation log channel was deleted and automatically restored.",
                discord.Color.orange()
            )

            await new_channel.send(embed=embed)

        # =========================
        # BOT LOG RECREATE
        # =========================
        elif channel.id == bot_log_id:

            await asyncio.sleep(1)

            new_channel = await channel.guild.create_text_channel(
                BOT_LOG_NAME,
                reason="Recreated deleted bot log"
            )

            cursor.execute(
                "UPDATE log_channels SET bot_log=? WHERE guild_id=?",
                (new_channel.id, channel.guild.id)
            )

            db.commit()

            embed = embed_builder(
                "♻️ Bot Log Recreated",
                "The bot log channel was deleted and automatically restored.",
                discord.Color.orange()
            )

            await new_channel.send(embed=embed)

    # =========================
    # SETUP COMMAND
    # =========================
    @commands.hybrid_command(
        name="setuplogs",
        help="Setup the entire logging system.",
        extras={
            "example": "!setuplogs",
            "tips": "Automatically creates categories and channels."
        }
    )
    @commands.has_permissions(administrator=True)
    async def setuplogs(self, ctx):
        """Setup logging channels."""

        await self.create_logs(ctx.guild)

        embed = embed_builder(
            "✅ Logs Setup Complete",
            (
                "The advanced logging system has been configured successfully.\n\n"
                "Created:\n"
                "• mod-logs\n"
                "• bot-logs"
            ),
            discord.Color.green()
        )

        await ctx.send(embed=embed)

    # =========================
    # RESET COMMAND
    # =========================
    @commands.hybrid_command(
        name="resetlogs",
        help="Reset all log channels.",
        extras={
            "example": "!resetlogs",
            "tips": "Deletes old saved channel IDs and recreates logs."
        }
    )
    @commands.has_permissions(administrator=True)
    async def resetlogs(self, ctx):
        """Reset logging system."""

        cursor.execute(
            "DELETE FROM log_channels WHERE guild_id=?",
            (ctx.guild.id,)
        )

        db.commit()

        await self.create_logs(ctx.guild)

        embed = embed_builder(
            "♻️ Logs Reset",
            "The logging system has been rebuilt successfully.",
            discord.Color.orange()
        )

        await ctx.send(embed=embed)

    # =========================
    # VIEW LOG CHANNELS
    # =========================
    @commands.hybrid_command(
        name="logchannels",
        help="View configured log channels.",
        extras={
            "example": "!logchannels",
            "tips": "Shows all active log channels."
        }
    )
    async def logchannels(self, ctx):
        """View configured logs."""

        logs = get_logs(ctx.guild.id)

        if not logs:
            return await ctx.send("❌ No logs configured")

        mod_log = ctx.guild.get_channel(logs[0])
        bot_log = ctx.guild.get_channel(logs[1])

        embed = embed_builder(
            "📄 Log Channels",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🛡️ Moderation Logs",
            value=mod_log.mention if mod_log else "Missing",
            inline=False
        )

        embed.add_field(
            name="🤖 Bot Logs",
            value=bot_log.mention if bot_log else "Missing",
            inline=False
        )

        await ctx.send(embed=embed)


# =========================
# SETUP
# =========================
async def setup(bot):

    await bot.add_cog(SetupLogs(bot))
