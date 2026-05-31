import asyncio
import discord

from datetime import timedelta
from discord.ext import commands
from discord import app_commands

from utils.dispatch import dispatch_log


MOD_COLOR = 0x2B2D31
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
            color=color,
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(
            text="Dem Moderation System"
        )

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

        if target == target.guild.owner:

            return False

        if moderator == moderator.guild.owner:

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

        except Exception:

            pass

    # ==================================================
    # KICK
    # ==================================================

    @commands.hybrid_command(name="kick")

    @commands.cooldown(
        2,
        10,
        commands.BucketType.user
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

    @commands.hybrid_command(name="ban")

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

            return await ctx.send(

                embed=self.embed(

                    description="❌ Cannot moderate this user.",

                    color=ERROR

                )

            )

        await self.dm_user(
            member,
            "banned",
            reason
        )

        await member.ban(

            reason=reason,

            delete_message_seconds=(
                delete_days * 86400
            )

        )

        await ctx.send(

            embed=self.embed(

                title="🔨 Member Banned",

                description=(
                    f"{member.mention}\n"
                    f"Reason: {reason}"
                ),

                color=ERROR

            )

        )

        await dispatch_log(

            ctx.guild,

            "ban",

            content=f"{member} banned",

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

        if minutes <= 0:

            return await ctx.send(
                "Invalid duration."
            )

        if not await self.can_moderate(
            ctx.author,
            member
        ):

            return

        await member.ban(
            reason=reason
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

            except Exception:

                pass

        asyncio.create_task(
            unban_later()
        )

        await ctx.send(

            embed=self.embed(

                title="⏳ Tempban",

                description=(
                    f"{member.mention}\n"
                    f"{minutes} minutes"
                ),

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

        await ctx.send(

            embed=self.embed(

                title="🔇 Timeout",

                description=(
                    f"{member.mention}\n"
                    f"{minutes} minutes"
                )

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
        member: discord.Member
    ):

        if not await self.can_moderate(
            ctx.author,
            member
        ):

            return

        await member.timeout(
            None
        )

        await ctx.send(

            embed=self.embed(

                description="✅ Timeout removed",

                color=SUCCESS

            )

        )


async def setup(bot):

    await bot.add_cog(
        Moderation(bot)
    )
