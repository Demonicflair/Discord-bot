# automod.py

import discord
from discord.ext import commands
import time
import sqlite3
import re

from utils.logger import get_logs, save_log, is_log_enabled

# =========================
# DATABASE
# =========================
db = sqlite3.connect("automod.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS automod_whitelist(
    guild_id INTEGER,
    user_id INTEGER
)
""")

db.commit()

# =========================
# CONFIG
# =========================
SPAM_LIMIT = 6
SPAM_TIME = 5

MENTION_LIMIT = 5
CAPS_PERCENT = 70
DUPLICATE_LIMIT = 3

BAD_LINKS = [
    "discord.gg/",
    "discord.com/invite/",
    "grabify",
    "iplogger"
]

# =========================
# MEMORY
# =========================
user_messages = {}
duplicate_cache = {}
user_warns = {}


# =========================
# EMBED
# =========================
def embed_builder(title, description, color=discord.Color.red()):

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    return embed


# =========================
# LOGGING
# =========================
async def send_log(guild, log_type, embed):

    logs = get_logs(guild.id)

    if not logs:
        return

    if not is_log_enabled(guild.id, log_type):
        return

    channel = guild.get_channel(logs[1])

    if not channel:
        return

    try:
        await channel.send(embed=embed)

    except:
        pass


# =========================
# AUTOMOD
# =========================
class AutoMod(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # WHITELIST CHECK
    # =========================
    def is_whitelisted(self, guild_id, user_id):

        cursor.execute(
            "SELECT * FROM automod_whitelist WHERE guild_id=? AND user_id=?",
            (guild_id, user_id)
        )

        return cursor.fetchone() is not None

    # =========================
    # AI PUNISHMENT
    # =========================
    async def punish(self, message, reason):

        guild = message.guild
        user = message.author

        if self.is_whitelisted(guild.id, user.id):
            return

        user_warns[user.id] = user_warns.get(user.id, 0) + 1

        warns = user_warns[user.id]

        # =========================
        # DELETE MESSAGE
        # =========================
        try:
            await message.delete()

        except:
            pass

        # =========================
        # WARN
        # =========================
        if warns == 1:

            embed = embed_builder(
                "⚠️ Warning",
                f"{user.mention}\nReason: {reason}",
                discord.Color.orange()
            )

            await message.channel.send(embed=embed, delete_after=5)

        # =========================
        # TIMEOUT
        # =========================
        elif warns >= 2:

            try:

                until = discord.utils.utcnow() + discord.timedelta(minutes=5)

                await user.timeout(
                    until,
                    reason=f"AutoMod: {reason}"
                )

                embed = embed_builder(
                    "🔇 Auto Timeout",
                    (
                        f"{user.mention} has been timed out.\n"
                        f"Reason: {reason}"
                    )
                )

                await message.channel.send(embed=embed)

            except:
                pass

        # =========================
        # LOG
        # =========================
        log_embed = embed_builder(
            "🛡️ AutoMod Triggered",
            (
                f"👤 User: {user.mention}\n"
                f"📍 Channel: {message.channel.mention}\n"
                f"⚠️ Reason: {reason}\n"
                f"📈 Warn Count: {warns}"
            )
        )

        await send_log(guild, "automod", log_embed)

        save_log(
            guild.id,
            user.id,
            "automod",
            f"{user} triggered automod: {reason}"
        )

    # =========================
    # MESSAGE DETECTION
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):

        if not message.guild:
            return

        if message.author.bot:
            return

        if self.is_whitelisted(message.guild.id, message.author.id):
            return

        uid = message.author.id
        now = time.time()

        # =========================
        # SPAM DETECTION
        # =========================
        user_messages.setdefault(uid, [])

        user_messages[uid].append(now)

        user_messages[uid] = [
            t for t in user_messages[uid]
            if now - t < SPAM_TIME
        ]

        if len(user_messages[uid]) >= SPAM_LIMIT:

            await self.punish(
                message,
                "Spam detected"
            )

            return

        # =========================
        # CAPS DETECTION
        # =========================
        if len(message.content) >= 8:

            upper = sum(1 for c in message.content if c.isupper())
            letters = sum(1 for c in message.content if c.isalpha())

            if letters > 0:

                percent = (upper / letters) * 100

                if percent >= CAPS_PERCENT:

                    await self.punish(
                        message,
                        "Excessive caps"
                    )

                    return

        # =========================
        # MENTION SPAM
        # =========================
        if len(message.mentions) >= MENTION_LIMIT:

            await self.punish(
                message,
                "Mention spam"
            )

            return

        # =========================
        # DUPLICATE DETECTION
        # =========================
        duplicate_cache.setdefault(uid, [])

        duplicate_cache[uid].append(message.content.lower())

        duplicate_cache[uid] = duplicate_cache[uid][-DUPLICATE_LIMIT:]

        if (
            len(duplicate_cache[uid]) >= DUPLICATE_LIMIT
            and len(set(duplicate_cache[uid])) == 1
        ):

            await self.punish(
                message,
                "Duplicate spam"
            )

            return

        # =========================
        # LINK DETECTION
        # =========================
        text = message.content.lower()

        for link in BAD_LINKS:

            if link in text:

                await self.punish(
                    message,
                    "Suspicious link"
                )

                return

        # =========================
        # INVITE REGEX
        # =========================
        if re.search(r"(discord\.gg/|discord\.com/invite/)", text):

            await self.punish(
                message,
                "Discord invite detected"
            )

            return

    # =========================
    # WHITELIST ADD
    # =========================
    @commands.hybrid_command(
        name="automod_whitelist",
        help="Whitelist a user from automod.",
        extras={
            "example": "!automod_whitelist @user",
            "tips": "Trusted users only."
        }
    )
    @commands.has_permissions(administrator=True)
    async def automod_whitelist(
        self,
        ctx,
        user: discord.Member = None
    ):
        """Whitelist a user."""

        if not user:
            return await ctx.send("❌ Usage: !automod_whitelist @user")

        cursor.execute(
            "INSERT INTO automod_whitelist VALUES (?, ?)",
            (ctx.guild.id, user.id)
        )

        db.commit()

        embed = embed_builder(
            "✅ Whitelisted",
            f"{user.mention} is now ignored by AutoMod.",
            discord.Color.green()
        )

        await ctx.send(embed=embed)

    # =========================
    # WHITELIST REMOVE
    # =========================
    @commands.hybrid_command(
        name="automod_unwhitelist",
        help="Remove automod whitelist.",
        extras={
            "example": "!automod_unwhitelist @user",
            "tips": "User will be monitored again."
        }
    )
    @commands.has_permissions(administrator=True)
    async def automod_unwhitelist(
        self,
        ctx,
        user: discord.Member = None
    ):
        """Remove whitelist."""

        if not user:
            return await ctx.send("❌ Usage: !automod_unwhitelist @user")

        cursor.execute(
            "DELETE FROM automod_whitelist WHERE guild_id=? AND user_id=?",
            (ctx.guild.id, user.id)
        )

        db.commit()

        embed = embed_builder(
            "❌ Removed Whitelist",
            f"{user.mention} is now monitored again.",
            discord.Color.red()
        )

        await ctx.send(embed=embed)

    # =========================
    # AUTOMOD STATUS
    # =========================
    @commands.hybrid_command(
        name="automod",
        help="View automod protections.",
        extras={
            "example": "!automod",
            "tips": "Shows active detections."
        }
    )
    async def automod(self, ctx):
        """View automod system."""

        embed = discord.Embed(
            title="🛡️ Advanced AutoMod",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="⚡ Spam Detection",
            value=f"{SPAM_LIMIT} messages / {SPAM_TIME}s"
        )

        embed.add_field(
            name="🔠 Caps Detection",
            value=f"{CAPS_PERCENT}%+ caps"
        )

        embed.add_field(
            name="🔔 Mention Spam",
            value=f"{MENTION_LIMIT}+ mentions"
        )

        embed.add_field(
            name="📄 Duplicate Detection",
            value=f"{DUPLICATE_LIMIT} repeated messages"
        )

        embed.add_field(
            name="🔗 Suspicious Links",
            value="Enabled"
        )

        await ctx.send(embed=embed)


# =========================
# SETUP
# =========================
async def setup(bot):

    await bot.add_cog(AutoMod(bot))
