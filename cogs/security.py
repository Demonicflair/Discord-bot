import re
import time
import datetime
import discord
import aiosqlite

from discord.ext import commands, tasks
from discord import app_commands

from utils.dispatch import dispatch_log
from utils.database import DB_PATH
from utils.config import (
    BRAND_COLOR,
    SCAM_PATTERN,
    BAD_WORDS,
    ANTI_LINK
)

# =========================
# SECURITY PATTERNS
# =========================

SCAM_PATTERNS = [
    r"free.*nitro",
    r"nitro.*free",
    r"steam.*gift",
    r"claim.*reward",
    r"discord.*gift",
    r"free.*robux",
    r"@everyone.*gift",
    r"cheap.*nitro",
    r"airdrop",
    r"crypto.*reward"
]

# Add config pattern too
SCAM_PATTERNS.append(SCAM_PATTERN)


# =========================
# SECURITY AI SYSTEM
# =========================

class SecurityAI(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # Memory Heat Cache
        self.heat_levels = {}

        # Spam Tracking
        self.message_cache = {}

        # Auto cooldown cleaner
        self.clean_heat.start()

    # =========================
    # DATABASE SETTING
    # =========================

    async def get_security_setting(
        self,
        guild_id: int,
        feature: str
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT enabled
                FROM settings
                WHERE guild_id=? AND feature=?
                """,
                (guild_id, feature)
            ) as cursor:

                data = await cursor.fetchone()

                # Default enabled
                return True if data is None else bool(data[0])

    # =========================
    # HEAT SYSTEM
    # =========================

    async def add_heat(
        self,
        message: discord.Message,
        amount: int,
        reason: str
    ):

        if message.author.guild_permissions.manage_messages:
            return

        key = (
            message.guild.id,
            message.author.id
        )

        current = self.heat_levels.get(key, 0)

        current += amount

        self.heat_levels[key] = current

        # Save persistent score
        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                INSERT OR REPLACE INTO security_scores
                (user_id, guild_id, score)
                VALUES (?, ?, ?)
            """, (
                message.author.id,
                message.guild.id,
                current
            ))

            await db.commit()

        # =========================
        # WARNING
        # =========================

        if current >= 3 and current < 6:

            try:

                embed = discord.Embed(
                    title="⚠️ Security Warning",
                    description=(
                        f"{message.author.mention} suspicious activity detected."
                    ),
                    color=discord.Color.orange()
                )

                embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )

                embed.add_field(
                    name="Threat Level",
                    value=f"{current}/10",
                    inline=True
                )

                warn_msg = await message.channel.send(
                    embed=embed
                )

                await asyncio.sleep(8)

                await warn_msg.delete()

            except:
                pass

        # =========================
        # TIMEOUT
        # =========================

        elif current >= 6 and current < 10:

            try:

                await message.author.timeout(
                    discord.utils.utcnow() + datetime.timedelta(hours=1),
                    reason=f"Security AI: {reason}"
                )

                await dispatch_log(
                    guild=message.guild,
                    log_type="security",
                    content=(
                        f"🔇 User timed out automatically.\n"
                        f"Reason: {reason}\n"
                        f"Threat Level: {current}/10"
                    ),
                    user_id=message.author.id
                )

            except Exception as e:
                print(f"[SECURITY TIMEOUT ERROR] {e}")

        # =========================
        # BAN
        # =========================

        elif current >= 10:

            try:

                await message.author.ban(
                    reason=f"Security AI: {reason}"
                )

                await dispatch_log(
                    guild=message.guild,
                    log_type="security",
                    content=(
                        f"⛔ User banned automatically.\n"
                        f"Reason: {reason}\n"
                        f"Threat Level: {current}/10"
                    ),
                    user_id=message.author.id
                )

                self.heat_levels[key] = 0

            except Exception as e:
                print(f"[SECURITY BAN ERROR] {e}")

    # =========================
    # AUTO CLEANER
    # =========================

    @tasks.loop(minutes=30)
    async def clean_heat(self):

        remove = []

        for key, value in self.heat_levels.items():

            value -= 1

            if value <= 0:
                remove.append(key)

            else:
                self.heat_levels[key] = value

        for key in remove:
            del self.heat_levels[key]

    # =========================
    # MESSAGE SCAN
    # =========================

    @commands.Cog.listener()
    async def on_message(self, message):

        if not message.guild:
            return

        if message.author.bot:
            return

        content = message.content.lower()

        # =========================
        # BAD WORD FILTER
        # =========================

        badword_enabled = await self.get_security_setting(
            message.guild.id,
            "badword_filter"
        )

        if badword_enabled:

            for word in BAD_WORDS:

                if word.lower() in content:

                    try:
                        await message.delete()
                    except:
                        pass

                    await self.add_heat(
                        message,
                        2,
                        "Bad Language"
                    )

                    return

        # =========================
        # SCAM DETECTION
        # =========================

        scam_enabled = await self.get_security_setting(
            message.guild.id,
            "scam_protection"
        )

        if scam_enabled:

            for pattern in SCAM_PATTERNS:

                if re.search(pattern, content):

                    try:
                        await message.delete()
                    except:
                        pass

                    await self.add_heat(
                        message,
                        5,
                        "Scam Detection"
                    )

                    return

        # =========================
        # MASS MENTION
        # =========================

        mention_enabled = await self.get_security_setting(
            message.guild.id,
            "mention_protection"
        )

        if mention_enabled:

            if len(message.mentions) >= 5:

                try:
                    await message.delete()
                except:
                    pass

                await self.add_heat(
                    message,
                    4,
                    "Mass Mention Spam"
                )

                return

        # =========================
        # LINK FILTER
        # =========================

        anti_link_enabled = await self.get_security_setting(
            message.guild.id,
            "anti_link"
        )

        if anti_link_enabled and ANTI_LINK:

            if "http://" in content or "https://" in content:

                if not message.author.guild_permissions.manage_messages:

                    try:
                        await message.delete()
                    except:
                        pass

                    await self.add_heat(
                        message,
                        3,
                        "Unauthorized Link"
                    )

                    return

        # =========================
        # MESSAGE SPAM
        # =========================

        key = (
            message.guild.id,
            message.author.id
        )

        now = time.time()

        if key not in self.message_cache:
            self.message_cache[key] = []

        self.message_cache[key].append(now)

        # Keep last 5 seconds only
        self.message_cache[key] = [
            t for t in self.message_cache[key]
            if now - t <= 5
        ]

        # Spam Detection
        if len(self.message_cache[key]) >= 7:

            try:
                await message.channel.purge(
                    limit=7,
                    check=lambda m: m.author.id == message.author.id
                )
            except:
                pass

            await self.add_heat(
                message,
                4,
                "Message Spam"
            )

    # =========================
    # SECURITY GROUP
    # =========================

    @commands.hybrid_group(
        name="security",
        description="Manage Dem Security AI."
    )
    @commands.has_permissions(administrator=True)
    async def security(self, ctx):

        if ctx.invoked_subcommand is None:

            embed = discord.Embed(
                title="🛡️ Dem Security AI",
                description=(
                    "Advanced AI moderation and protection system.\n\n"
                    "Available Commands:\n"
                    "`/security status`\n"
                    "`/security reset`\n"
                    "`/security toggle`\n"
                    "`/security settings`"
                ),
                color=BRAND_COLOR
            )

            await ctx.send(embed=embed)

    # =========================
    # STATUS
    # =========================

    @security.command(
        name="status",
        description="View user threat level."
    )
    async def security_status(
        self,
        ctx,
        member: discord.Member
    ):

        heat = self.heat_levels.get(
            (ctx.guild.id, member.id),
            0
        )

        if heat < 3:
            status = "🟢 Safe"

        elif heat < 6:
            status = "🟡 Warning"

        else:
            status = "🔴 Dangerous"

        embed = discord.Embed(
            title="🛡️ Security Profile",
            color=BRAND_COLOR
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="User",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="Threat Level",
            value=f"{heat}/10",
            inline=True
        )

        embed.add_field(
            name="Status",
            value=status,
            inline=True
        )

        await ctx.send(embed=embed)

    # =========================
    # RESET
    # =========================

    @security.command(
        name="reset",
        description="Reset security heat."
    )
    async def security_reset(
        self,
        ctx,
        member: discord.Member
    ):

        self.heat_levels[
            (ctx.guild.id, member.id)
        ] = 0

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                UPDATE security_scores
                SET score=0
                WHERE user_id=? AND guild_id=?
            """, (
                member.id,
                ctx.guild.id
            ))

            await db.commit()

        await ctx.send(
            f"✅ Reset security heat for {member.mention}"
        )

    # =========================
    # TOGGLE FEATURES
    # =========================

    @security.command(
        name="toggle",
        description="Enable or disable security features."
    )
    async def security_toggle(
        self,
        ctx,
        feature: str,
        state: bool
    ):

        valid = [
            "scam_protection",
            "mention_protection",
            "anti_link",
            "badword_filter"
        ]

        if feature not in valid:

            return await ctx.send(
                f"❌ Invalid feature.\n\nValid Features:\n`{'`, `'.join(valid)}`"
            )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                INSERT OR REPLACE INTO settings
                (guild_id, feature, enabled)
                VALUES (?, ?, ?)
            """, (
                ctx.guild.id,
                feature,
                int(state)
            ))

            await db.commit()

        await ctx.send(
            f"✅ `{feature}` has been set to `{state}`"
        )

    # =========================
    # SETTINGS VIEW
    # =========================

    @security.command(
        name="settings",
        description="View current security settings."
    )
    async def security_settings(self, ctx):

        features = [
            "scam_protection",
            "mention_protection",
            "anti_link",
            "badword_filter"
        ]

        embed = discord.Embed(
            title="⚙️ Security Settings",
            color=BRAND_COLOR
        )

        for feature in features:

            enabled = await self.get_security_setting(
                ctx.guild.id,
                feature
            )

            embed.add_field(
                name=feature.replace("_", " ").title(),
                value="🟢 Enabled" if enabled else "🔴 Disabled",
                inline=True
            )

        await ctx.send(embed=embed)


# =========================
# LOAD COG
# =========================

async def setup(bot):

    await bot.add_cog(SecurityAI(bot))
