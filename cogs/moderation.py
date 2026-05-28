import time
import asyncio
import discord
import aiosqlite

from datetime import timedelta
from discord.ext import commands
from discord import app_commands

from utils.database import DB_PATH
from utils.dispatch import dispatch_log


MOD_COLOR = 0x2b2d31
SUCCESS = 0x57F287
ERROR = 0xED4245
WARNING = 0xFEE75C


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ==================================================
    # EMBED
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

        if moderator.id == target.id:
            return False

        if target.guild.owner == target:
            return False

        if moderator.guild.owner == moderator:
            return True

        bot_member = moderator.guild.me

        if target.top_role >= moderator.top_role:
            return False

        if bot_member and target.top_role >= bot_member.top_role:
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

            await member.send(

                embed=self.embed(

                    title=f"You were {action}",

                    description=(
                        f"Server: {member.guild.name}\n"
                        f"Reason: {reason}"
                    ),

                    color=ERROR

                )

            )

        except discord.HTTPException:

            pass

    # ==================================================
    # KICK
    # ==================================================

    @commands.hybrid_command(
        name="kick"
    )

    @commands.has_permissions(
        kick_members=True
    )

    async def kick(
        self,
        ctx,
        member: discord.Member,
        *,
        reason="No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):

            return await ctx.send(

                embed=self.embed(

                    description="❌ Cannot moderate this user.",

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

        await ctx.send(

            embed=self.embed(

                title="👢 Member Kicked",

                description=(
                    f"{member.mention}\n"
                    f"Reason: {reason}"
                ),

                color=WARNING

            )

        )

        await dispatch_log(

            ctx.guild,

            "kick",

            content=f"{member} kicked\nReason: {reason}",

            user_id=member.id,

            moderator_id=ctx.author.id

        )

    # ==================================================
    # BAN
    # ==================================================

    @commands.hybrid_command(
        name="ban"
    )

    @commands.has_permissions(
        ban_members=True
    )

    async def ban(
        self,
        ctx,
        member: discord.Member,
        delete_days: app_commands.Range[int,0,7]=0,
        *,
        reason="No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):
            return

        await self.dm_user(
            member,
            "banned",
            reason
        )

        await member.ban(
            reason=reason,
            delete_message_seconds=delete_days * 86400
        )

        await ctx.send(

            embed=self.embed(

                title="🔨 Member Banned",

                description=f"{member.mention}\nReason: {reason}",

                color=ERROR

            )

        )

        await dispatch_log(

            ctx.guild,

            "ban",

            content=f"{member} banned\nReason: {reason}",

            user_id=member.id,

            moderator_id=ctx.author.id

        )

    # ==================================================
    # TEMPBAN
    # ==================================================

    @commands.hybrid_command(
        name="tempban"
    )

    @commands.has_permissions(
        ban_members=True
    )

    async def tempban(
        self,
        ctx,
        member: discord.Member,
        minutes:int,
        *,
        reason="No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):
            return

        await member.ban(
            reason=reason
        )

        await dispatch_log(

            ctx.guild,

            "ban",

            content=f"{member} tempbanned ({minutes}m)",

            user_id=member.id,

            moderator_id=ctx.author.id

        )

        async def unban_later():

            await asyncio.sleep(
                minutes * 60
            )

            try:

                await ctx.guild.unban(
                    discord.Object(
                        id=member.id
                    )
                )

            except:

                pass

        self.bot.loop.create_task(
            unban_later()
        )

        await ctx.send(

            embed=self.embed(

                title="⏳ Tempban",

                description=f"{member} banned for {minutes} minutes",

                color=ERROR

            )

        )

    # ==================================================
    # TIMEOUT
    # ==================================================

    @commands.hybrid_command(
        name="timeout"
    )

    @commands.has_permissions(
        moderate_members=True
    )

    async def timeout(
        self,
        ctx,
        member: discord.Member,
        minutes:int,
        *,
        reason="No reason provided"
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):
            return

        await member.timeout(

            discord.utils.utcnow()

            + timedelta(
                minutes=minutes
            ),

            reason=reason

        )

        await dispatch_log(

            ctx.guild,

            "timeout",

            content=f"{member} timeout {minutes}m",

            user_id=member.id,

            moderator_id=ctx.author.id

        )

        await ctx.send(

            embed=self.embed(

                title="🔇 Timeout",

                description=f"{member.mention}\n{minutes} minutes"

            )

        )

    # ==================================================
    # UNTIMEOUT
    # ==================================================

    @commands.hybrid_command(
        name="untimeout"
    )

    @commands.has_permissions(
        moderate_members=True
    )

    async def untimeout(
        self,
        ctx,
        member:discord.Member
    ):

        await member.timeout(
            None
        )

        await dispatch_log(

            ctx.guild,

            "untimeout",

            content=f"{member} timeout removed",

            user_id=member.id,

            moderator_id=ctx.author.id

        )

        await ctx.send(

            embed=self.embed(

                description="✅ Timeout removed",

                color=SUCCESS

            )

        )

    # WARN / REMOVEWARN / WARNINGS / CLEAR / SOFTBAN / NICKNAME

    # keep your original implementations,
    # only replace DB_PATH imports and add can_moderate checks
    # because logic itself is already fine.

async def setup(bot):

    await bot.add_cog(
        Moderation(bot)
        )
