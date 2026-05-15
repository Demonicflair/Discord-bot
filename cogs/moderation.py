import time
import asyncio
import discord
import aiosqlite

from discord.ext import commands
from discord import app_commands

from utils.dispatch import dispatch_log

DB_PATH = "data.db"

MOD_COLOR = 0x2b2d31
SUCCESS = 0x57F287
ERROR = 0xED4245
WARNING = 0xFEE75C


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ==================================================
    # PREMIUM EMBED
    # ==================================================
    def embed(
        self,
        title=None,
        description=None,
        color=MOD_COLOR
    ):

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        embed.set_footer(
            text="Dem Moderation System"
        )

        embed.timestamp = discord.utils.utcnow()

        return embed

    # ==================================================
    # HIERARCHY CHECK
    # ==================================================
    async def can_moderate(
        self,
        moderator: discord.Member,
        target: discord.Member
    ):

        if moderator.guild.owner == moderator:
            return True

        if moderator.id == target.id:
            return False

        if target.guild.owner == target:
            return False

        if target.top_role >= moderator.top_role:
            return False

        if target.top_role >= moderator.guild.me.top_role:
            return False

        return True

    # ==================================================
    # DM USER
    # ==================================================
    async def dm_user(
        self,
        member,
        action,
        reason
    ):

        try:

            embed = self.embed(
                title=f"You were {action}",
                description=(
                    f"**Server:** {member.guild.name}\n"
                    f"**Reason:** {reason}"
                ),
                color=ERROR
            )

            await member.send(embed=embed)

        except:
            pass

    # ==================================================
    # KICK
    # ==================================================
    @commands.hybrid_command(
        name="kick",
        description="Kick a member."
    )
    @commands.has_permissions(
        kick_members=True
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
                embed=self.embed(
                    description="❌ You cannot moderate this user.",
                    color=ERROR
                )
            )

        await self.dm_user(
            member,
            "kicked",
            reason
        )

        await member.kick(
            reason=f"{ctx.author} | {reason}"
        )

        embed = self.embed(
            title="👢 Member Kicked",
            description=(
                f"{member.mention} has been removed.\n\n"
                f"**Reason:** {reason}"
            ),
            color=WARNING
        )

        await ctx.send(embed=embed)

        await dispatch_log(
            guild=ctx.guild,
            log_type="kick",
            content=(
                f"👢 User Kicked\n"
                f"User: {member} ({member.id})\n"
                f"Moderator: {ctx.author}\n"
                f"Reason: {reason}"
            ),
            user_id=member.id,
            moderator_id=ctx.author.id
        )

    # ==================================================
    # BAN
    # ==================================================
    @commands.hybrid_command(
        name="ban",
        description="Ban a member."
    )
    @commands.has_permissions(
        ban_members=True
    )
    async def ban(
        self,
        ctx,
        member: discord.Member,
        delete_days: app_commands.Range[int, 0, 7] = 0,
        *,
        reason: str = "No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):

            return await ctx.send(
                embed=self.embed(
                    description="❌ You cannot moderate this user.",
                    color=ERROR
                )
            )

        await self.dm_user(
            member,
            "banned",
            reason
        )

        await member.ban(
            reason=f"{ctx.author} | {reason}",
            delete_message_days=delete_days
        )

        embed = self.embed(
            title="🔨 Member Banned",
            description=(
                f"{member.mention} has been banned.\n\n"
                f"**Reason:** {reason}"
            ),
            color=ERROR
        )

        await ctx.send(embed=embed)

        await dispatch_log(
            guild=ctx.guild,
            log_type="ban",
            content=(
                f"🔨 User Banned\n"
                f"User: {member} ({member.id})\n"
                f"Moderator: {ctx.author}\n"
                f"Reason: {reason}"
            ),
            user_id=member.id,
            moderator_id=ctx.author.id
        )

    # ==================================================
    # TEMPBAN
    # ==================================================
    @commands.hybrid_command(
        name="tempban",
        description="Temporarily ban a member."
    )
    @commands.has_permissions(
        ban_members=True
    )
    async def tempban(
        self,
        ctx,
        member: discord.Member,
        minutes: int,
        *,
        reason: str = "No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):
            return await ctx.send(
                embed=self.embed(
                    description="❌ You cannot moderate this user.",
                    color=ERROR
                )
            )

        await member.ban(
            reason=f"Tempban | {reason}"
        )

        embed = self.embed(
            title="⏳ Temporary Ban",
            description=(
                f"{member.mention} banned for `{minutes}` minutes.\n\n"
                f"**Reason:** {reason}"
            ),
            color=ERROR
        )

        await ctx.send(embed=embed)

        async def unban_later():

            await asyncio.sleep(minutes * 60)

            try:
                await ctx.guild.unban(member)
            except:
                pass

        self.bot.loop.create_task(
            unban_later()
        )

    # ==================================================
    # TIMEOUT
    # ==================================================
    @commands.hybrid_command(
        name="timeout",
        description="Timeout a member."
    )
    @commands.has_permissions(
        moderate_members=True
    )
    async def timeout(
        self,
        ctx,
        member: discord.Member,
        minutes: int,
        *,
        reason: str = "No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):
            return

        until = discord.utils.utcnow() + discord.timedelta(
            minutes=minutes
        )

        await member.timeout(
            until,
            reason=reason
        )

        embed = self.embed(
            title="🔇 Member Timed Out",
            description=(
                f"{member.mention} timed out for `{minutes}` minutes.\n\n"
                f"**Reason:** {reason}"
            )
        )

        await ctx.send(embed=embed)

    # ==================================================
    # UNTIMEOUT
    # ==================================================
    @commands.hybrid_command(
        name="untimeout",
        description="Remove timeout from a member."
    )
    @commands.has_permissions(
        moderate_members=True
    )
    async def untimeout(
        self,
        ctx,
        member: discord.Member
    ):

        await member.timeout(None)

        embed = self.embed(
            title="🔊 Timeout Removed",
            description=f"{member.mention} is no longer timed out.",
            color=SUCCESS
        )

        await ctx.send(embed=embed)

    # ==================================================
    # WARN
    # ==================================================
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
            return

        async with aiosqlite.connect(DB_PATH) as db:

            cursor = await db.execute(
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

            warn_id = cursor.lastrowid

            await db.commit()

        embed = self.embed(
            title="⚠️ User Warned",
            description=(
                f"{member.mention} has been warned.\n\n"
                f"**Warning ID:** `{warn_id}`\n"
                f"**Reason:** {reason}"
            ),
            color=WARNING
        )

        await ctx.send(embed=embed)

    # ==================================================
    # REMOVE WARNING
    # ==================================================
    @commands.hybrid_command(
        name="removewarn",
        description="Remove a warning."
    )
    @commands.has_permissions(
        manage_messages=True
    )
    async def removewarn(
        self,
        ctx,
        warn_id: int
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                DELETE FROM warnings
                WHERE id = ?
                """,
                (warn_id,)
            )

            await db.commit()

        await ctx.send(
            embed=self.embed(
                description=f"✅ Removed warning `{warn_id}`",
                color=SUCCESS
            )
        )

    # ==================================================
    # PURGE
    # ==================================================
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
        amount: app_commands.Range[int, 1, 100]
    ):

        deleted = await ctx.channel.purge(
            limit=amount + 1
        )

        msg = await ctx.send(
            embed=self.embed(
                description=f"🧹 Deleted `{len(deleted)-1}` messages.",
                color=SUCCESS
            )
        )

        await asyncio.sleep(5)

        await msg.delete()

    # ==================================================
    # SOFTBAN
    # ==================================================
    @commands.hybrid_command(
        name="softban",
        description="Softban a member."
    )
    @commands.has_permissions(
        ban_members=True
    )
    async def softban(
        self,
        ctx,
        member: discord.Member,
        *,
        reason: str = "No reason provided"
    ):

        await member.ban(
            delete_message_days=1,
            reason=reason
        )

        await ctx.guild.unban(member)

        await ctx.send(
            embed=self.embed(
                title="🧹 Softban Executed",
                description=(
                    f"{member.mention} was softbanned.\n\n"
                    f"**Reason:** {reason}"
                ),
                color=WARNING
            )
        )

    # ==================================================
    # NICKNAME
    # ==================================================
    @commands.hybrid_command(
        name="nickname",
        description="Change a member's nickname."
    )
    @commands.has_permissions(
        manage_nicknames=True
    )
    async def nickname(
        self,
        ctx,
        member: discord.Member,
        *,
        nickname: str
    ):

        await member.edit(
            nick=nickname
        )

        await ctx.send(
            embed=self.embed(
                description=(
                    f"✏️ Updated nickname for "
                    f"{member.mention}"
                ),
                color=SUCCESS
            )
        )

    # ==================================================
    # WARNINGS
    # ==================================================
    @commands.hybrid_command(
        name="warnings",
        description="View warnings."
    )
    async def warnings(
        self,
        ctx,
        member: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT id, reason, moderator_id, timestamp
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
                embed=self.embed(
                    description=(
                        f"✅ {member.mention} "
                        f"has no warnings."
                    ),
                    color=SUCCESS
                )
            )

        embed = self.embed(
            title=f"⚠️ Warnings for {member}",
            color=WARNING
        )

        for warn in data[:10]:

            warn_id, reason, moderator_id, timestamp = warn

            embed.add_field(
                name=f"Warning #{warn_id}",
                value=(
                    f"**Reason:** {reason}\n"
                    f"**Moderator:** <@{moderator_id}>\n"
                    f"**Time:** <t:{timestamp}:R>"
                ),
                inline=False
            )

        await ctx.send(embed=embed)


async def setup(bot):

    await bot.add_cog(
        Moderation(bot)
        )
