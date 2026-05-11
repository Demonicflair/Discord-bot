import time
import discord
import aiosqlite

from discord.ext import commands
from discord import app_commands

from utils.dispatch import dispatch_log

DB_PATH = "data.db"
MOD_COLOR = 0x2b2d31


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # HIERARCHY CHECK
    # =========================
    async def can_moderate(
        self,
        moderator: discord.Member,
        target: discord.Member
    ):

        # Owner bypass
        if moderator.guild.owner == moderator:
            return True

        # Can't moderate yourself
        if moderator.id == target.id:
            return False

        # Can't moderate higher/equal role
        if target.top_role >= moderator.top_role:
            return False

        # Can't moderate bot owner
        if target.guild.owner == target:
            return False

        return True

    # =========================
    # KICK COMMAND
    # =========================
    @commands.hybrid_command(
        name="kick",
        description="Kick a member from the server."
    )
    @commands.has_permissions(
        kick_members=True
    )
    @app_commands.describe(
        member="Member to kick",
        reason="Reason for the kick"
    )
    async def kick(
        self,
        ctx,
        member: discord.Member,
        *,
        reason: str = "No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):

            return await ctx.send(
                "❌ You cannot moderate this user."
            )

        try:

            await member.kick(
                reason=f"{ctx.author} | {reason}"
            )

            embed = discord.Embed(
                description=(
                    f"👢 {member.mention} was kicked.\n"
                    f"**Reason:** {reason}"
                ),
                color=discord.Color.orange()
            )

            await ctx.send(embed=embed)

            await dispatch_log(
                guild=ctx.guild,
                log_type="kick",
                content=(
                    f"👢 **Kick Action**\n"
                    f"**User:** {member} ({member.id})\n"
                    f"**Moderator:** {ctx.author}\n"
                    f"**Reason:** {reason}"
                ),
                user_id=member.id,
                moderator_id=ctx.author.id
            )

        except Exception as error:

            await ctx.send(
                f"❌ Failed to kick user.\n`{error}`"
            )

    # =========================
    # BAN COMMAND
    # =========================
    @commands.hybrid_command(
        name="ban",
        description="Ban a member from the server."
    )
    @commands.has_permissions(
        ban_members=True
    )
    @app_commands.describe(
        member="Member to ban",
        delete_days="Delete message history",
        reason="Reason for the ban"
    )
    async def ban(
        self,
        ctx,
        member: discord.Member,
        delete_days: int = 0,
        *,
        reason: str = "No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):

            return await ctx.send(
                "❌ You cannot moderate this user."
            )

        try:

            await member.ban(
                reason=f"{ctx.author} | {reason}",
                delete_message_days=delete_days
            )

            embed = discord.Embed(
                description=(
                    f"🔨 {member.mention} was banned.\n"
                    f"**Reason:** {reason}"
                ),
                color=discord.Color.red()
            )

            await ctx.send(embed=embed)

            await dispatch_log(
                guild=ctx.guild,
                log_type="ban",
                content=(
                    f"🔨 **Ban Action**\n"
                    f"**User:** {member} ({member.id})\n"
                    f"**Moderator:** {ctx.author}\n"
                    f"**Reason:** {reason}"
                ),
                user_id=member.id,
                moderator_id=ctx.author.id
            )

        except Exception as error:

            await ctx.send(
                f"❌ Failed to ban user.\n`{error}`"
            )

    # =========================
    # UNBAN COMMAND
    # =========================
    @commands.hybrid_command(
        name="unban",
        description="Unban a user."
    )
    @commands.has_permissions(
        ban_members=True
    )
    async def unban(
        self,
        ctx,
        user_id: int
    ):

        try:

            user = await self.bot.fetch_user(
                user_id
            )

            await ctx.guild.unban(user)

            embed = discord.Embed(
                description=(
                    f"✅ Unbanned {user}"
                ),
                color=discord.Color.green()
            )

            await ctx.send(embed=embed)

            await dispatch_log(
                guild=ctx.guild,
                log_type="unban",
                content=(
                    f"✅ **Unban Action**\n"
                    f"**User:** {user} ({user.id})\n"
                    f"**Moderator:** {ctx.author}"
                ),
                user_id=user.id,
                moderator_id=ctx.author.id
            )

        except Exception as error:

            await ctx.send(
                f"❌ Failed to unban user.\n`{error}`"
            )

    # =========================
    # WARN COMMAND
    # =========================
    @commands.hybrid_command(
        name="warn",
        description="Warn a member."
    )
    @commands.has_permissions(
        manage_messages=True
    )
    async def warn(
        self,
        ctx,
        member: discord.Member,
        *,
        reason: str = "No reason provided"
    ):

        if member.bot:

            return await ctx.send(
                "❌ You cannot warn bots."
            )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT INTO warnings
                (
                    user_id,
                    guild_id,
                    reason,
                    moderator_id,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    member.id,
                    ctx.guild.id,
                    reason,
                    ctx.author.id,
                    int(time.time())
                )
            )

            await db.commit()

        embed = discord.Embed(
            description=(
                f"⚠️ {member.mention} has been warned.\n"
                f"**Reason:** {reason}"
            ),
            color=MOD_COLOR
        )

        await ctx.send(embed=embed)

        await dispatch_log(
            guild=ctx.guild,
            log_type="warn",
            content=(
                f"⚠️ **Warning Issued**\n"
                f"**User:** {member} ({member.id})\n"
                f"**Moderator:** {ctx.author}\n"
                f"**Reason:** {reason}"
            ),
            user_id=member.id,
            moderator_id=ctx.author.id
        )

    # =========================
    # CLEAR COMMAND
    # =========================
    @commands.hybrid_command(
        name="clear",
        description="Delete messages."
    )
    @commands.has_permissions(
        manage_messages=True
    )
    async def clear(
        self,
        ctx,
        amount: int
    ):

        if amount <= 0:

            return await ctx.send(
                "❌ Amount must be above 0."
            )

        if amount > 100:

            return await ctx.send(
                "❌ Maximum is 100 messages."
            )

        deleted = await ctx.channel.purge(
            limit=amount + 1
        )

        msg = await ctx.send(
            f"🧹 Deleted `{len(deleted) - 1}` messages."
        )

        await dispatch_log(
            guild=ctx.guild,
            log_type="clear",
            content=(
                f"🧹 **Messages Cleared**\n"
                f"**Moderator:** {ctx.author}\n"
                f"**Amount:** {len(deleted) - 1}\n"
                f"**Channel:** {ctx.channel.mention}"
            ),
            moderator_id=ctx.author.id
        )

        await msg.delete(delay=5)

    # =========================
    # WARNS COMMAND
    # =========================
    @commands.hybrid_command(
        name="warnings",
        description="Check a user's warnings."
    )
    async def warnings(
        self,
        ctx,
        member: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT reason, moderator_id, timestamp
                FROM warnings
                WHERE user_id = ?
                AND guild_id = ?
                ORDER BY timestamp DESC
                """,
                (
                    member.id,
                    ctx.guild.id
                )
            ) as cursor:

                data = await cursor.fetchall()

        if not data:

            return await ctx.send(
                f"✅ {member} has no warnings."
            )

        embed = discord.Embed(
            title=f"⚠️ Warnings for {member}",
            color=MOD_COLOR
        )

        for index, warn in enumerate(
            data[:10],
            start=1
        ):

            reason, moderator_id, timestamp = warn

            embed.add_field(
                name=f"Warning #{index}",
                value=(
                    f"**Reason:** {reason}\n"
                    f"**Moderator:** <@{moderator_id}>\n"
                    f"**Time:** <t:{timestamp}:R>"
                ),
                inline=False
            )

        await ctx.send(embed=embed)


# =========================
# LOAD COG
# =========================
async def setup(bot):

    await bot.add_cog(
        Moderation(bot)
    )
