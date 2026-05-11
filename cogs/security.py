import re
import datetime
import discord
import aiosqlite

from discord.ext import commands
from discord import app_commands

from utils.dispatch import dispatch_log
from utils.database import DB_PATH

# =========================
# SCAM PATTERNS
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


# =========================
# SECURITY COG
# =========================

class SecurityAI(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # {(guild_id, user_id): heat}
        self.heat_levels = {}

    # =========================
    # DATABASE SETTINGS
    # =========================

    async def get_security_setting(
        self,
        guild_id,
        feature
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

                # Default ON
                return data is None or bool(data[0])

    # =========================
    # HEAT SYSTEM
    # =========================

    async def add_heat(
        self,
        message,
        amount,
        reason
    ):

        # Ignore staff
        if message.author.guild_permissions.manage_messages:
            return

        key = (
            message.guild.id,
            message.author.id
        )

        current_heat = self.heat_levels.get(key, 0)
        current_heat += amount

        self.heat_levels[key] = current_heat

        # =========================
        # WARNING
        # =========================

        if current_heat >= 3 and current_heat < 6:

            try:
                await message.channel.send(
                    f"⚠️ {message.author.mention} suspicious activity detected.\n"
                    f"Reason: `{reason}`",
                    delete_after=6
                )
            except:
                pass

        # =========================
        # TIMEOUT
        # =========================

        elif current_heat >= 6 and current_heat < 10:

            try:
                await message.author.timeout(
                    discord.utils.utcnow() + datetime.timedelta(hours=1),
                    reason=f"Security AI: {reason}"
                )

                await dispatch_log(
                    message.guild,
                    "security",
                    content=(
                        f"🔇 **User Timed Out**\n"
                        f"User: {message.author}\n"
                        f"Heat: {current_heat}/10\n"
                        f"Reason: {reason}"
                    ),
                    user_id=message.author.id
                )

            except Exception as e:
                print(f"[SECURITY TIMEOUT ERROR] {e}")

        # =========================
        # BAN
        # =========================

        elif current_heat >= 10:

            try:
                await message.author.ban(
                    reason=f"Security AI: {reason}"
                )

                await dispatch_log(
                    message.guild,
                    "security",
                    content=(
                        f"⛔ **User Banned by Security AI**\n"
                        f"User: {message.author}\n"
                        f"Heat: {current_heat}/10\n"
                        f"Reason: {reason}"
                    ),
                    user_id=message.author.id
                )

                # Reset after ban
                self.heat_levels[key] = 0

            except Exception as e:
                print(f"[SECURITY BAN ERROR] {e}")

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
                    "Mass Mention"
                )

                return

        # =========================
        # LINK SPAM
        # =========================

        link_enabled = await self.get_security_setting(
            message.guild.id,
            "anti_link"
        )

        if link_enabled:

            if "http://" in content or "https://" in content:

                if len(content) > 120:

                    try:
                        await message.delete()
                    except:
                        pass

                    await self.add_heat(
                        message,
                        3,
                        "Suspicious Link"
                    )

    # =========================
    # SECURITY GROUP
    # =========================

    @commands.hybrid_group(
        name="security",
        description="Manage AI security system."
    )
    @commands.has_permissions(administrator=True)
    async def security(self, ctx):

        if ctx.invoked_subcommand is None:

            embed = discord.Embed(
                title="🛡️ Security System",
                description=(
                    "`/security status`\n"
                    "`/security reset`\n"
                    "`/security settings`"
                ),
                color=0x2b2d31
            )

            await ctx.send(embed=embed)

    # =========================
    # SECURITY STATUS
    # =========================

    @security.command(
        name="status",
        description="View AI heat level."
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
            color=0x2b2d31
        )

        embed.add_field(
            name="User",
            value=member.mention
        )

        embed.add_field(
            name="Heat",
            value=f"{heat}/10"
        )

        embed.add_field(
            name="Status",
            value=status
        )

        await ctx.send(embed=embed)

    # =========================
    # RESET HEAT
    # =========================

    @security.command(
        name="reset",
        description="Reset AI heat."
    )
    async def security_reset(
        self,
        ctx,
        member: discord.Member
    ):

        self.heat_levels[
            (ctx.guild.id, member.id)
        ] = 0

        await ctx.send(
            f"✅ Reset heat for {member.mention}"
        )

    # =========================
    # TOGGLE SETTINGS
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
            "anti_link"
        ]

        if feature not in valid:

            return await ctx.send(
                f"❌ Invalid feature.\nValid:\n{', '.join(valid)}"
            )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT OR REPLACE INTO settings
                (guild_id, feature, enabled)
                VALUES (?, ?, ?)
                """,
                (
                    ctx.guild.id,
                    feature,
                    int(state)
                )
            )

            await db.commit()

        await ctx.send(
            f"✅ `{feature}` set to `{state}`"
        )


# =========================
# LOAD COG
# =========================

async def setup(bot):
    await bot.add_cog(SecurityAI(bot))
