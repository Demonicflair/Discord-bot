import asyncio
import discord

from datetime import timedelta
from discord.ext import commands
from discord import app_commands

from utils.dispatch import dispatch_log
from utils.config import BRAND_COLOR


SUCCESS = 0x57F287
ERROR = 0xED4245
WARNING = 0xFEE75C


class Moderation(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # ==========================================
    # EMBED
    # ==========================================

    def embed(
        self,
        title=None,
        description=None,
        color=BRAND_COLOR
    ):

        embed=discord.Embed(

            title=title,

            description=description,

            color=color,

            timestamp=discord.utils.utcnow()

        )

        embed.set_footer(

            text="Dem Moderation"

        )

        return embed

    # ==========================================
    # CHECKS
    # ==========================================

    async def can_moderate(

        self,

        moderator:discord.Member,

        target:discord.Member

    ):

        if moderator.id == target.id:

            return False

        if target.guild.owner == target:

            return False

        if moderator.guild.owner == moderator:

            return True

        bot_member=target.guild.me

        if target.top_role >= moderator.top_role:

            return False

        if bot_member:

            if target.top_role >= bot_member.top_role:

                return False

        return True

    async def fail(
        self,
        ctx,
        text
    ):

        await ctx.send(

            embed=self.embed(

                description=f"❌ {text}",

                color=ERROR

            )

        )

    # ==========================================
    # DM
    # ==========================================

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

        except:

            pass

    # ==========================================
    # KICK
    # ==========================================

    @commands.hybrid_command()

    @commands.has_permissions(
        kick_members=True
    )

    @commands.bot_has_permissions(
        kick_members=True
    )

    async def kick(

        self,

        ctx,

        member:discord.Member,

        *,

        reason="No reason provided"

    ):

        if not await self.can_moderate(

            ctx.author,

            member

        ):

            return await self.fail(

                ctx,

                "Cannot moderate this user."

            )

        try:

            await self.dm_user(

                member,

                "kicked",

                reason

            )

            await member.kick(

                reason=f"{ctx.author} | {reason}"

            )

        except Exception:

            return await self.fail(

                ctx,

                "Kick failed."

            )

        await ctx.send(

            embed=self.embed(

                title="Member Kicked",

                description=f"{member.mention}\nReason: {reason}",

                color=WARNING

            )

        )

        await dispatch_log(

            ctx.guild,

            "kick",

            content=f"{member} kicked\n{reason}",

            user_id=member.id,

            moderator_id=ctx.author.id

        )

    # ==========================================
    # BAN
    # ==========================================

    @commands.hybrid_command()

    @commands.has_permissions(
        ban_members=True
    )

    @commands.bot_has_permissions(
        ban_members=True
    )

    async def ban(

        self,

        ctx,

        member:discord.Member,

        delete_days:app_commands.Range[int,0,7]=0,

        *,

        reason="No reason provided"

    ):

        if not await self.can_moderate(

            ctx.author,

            member

        ):

            return await self.fail(

                ctx,

                "Cannot moderate this user."

            )

        try:

            await self.dm_user(

                member,

                "banned",

                reason

            )

            await member.ban(

                reason=reason,

                delete_message_seconds=(

                    delete_days*86400

                )

            )

        except:

            return await self.fail(

                ctx,

                "Ban failed."

            )

        await ctx.send(

            embed=self.embed(

                title="Member Banned",

                description=f"{member.mention}\nReason: {reason}",

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

    # ==========================================
    # TEMPBAN
    # ==========================================

    @commands.hybrid_command()

    @commands.has_permissions(
        ban_members=True
    )

    async def tempban(

        self,

        ctx,

        member:discord.Member,

        minutes:int,

        *,

        reason="No reason"

    ):

        if minutes <= 0:

            return await self.fail(

                ctx,

                "Duration must be positive."

            )

        if not await self.can_moderate(

            ctx.author,

            member

        ):

            return await self.fail(

                ctx,

                "Cannot moderate user."

            )

        await member.ban(

            reason=reason

        )

        async def unban():

            await asyncio.sleep(

                minutes*60

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

            unban()

        )

        await ctx.send(

            embed=self.embed(

                title="Temporary Ban",

                description=(

                    f"{member.mention}\n"

                    f"Duration: {minutes} minutes"

                ),

                color=ERROR

            )

        )

    # ==========================================
    # TIMEOUT
    # ==========================================

    @commands.hybrid_command()

    @commands.has_permissions(
        moderate_members=True
    )

    async def timeout(

        self,

        ctx,

        member:discord.Member,

        minutes:int,

        *,

        reason="No reason"

    ):

        if minutes <= 0:

            return await self.fail(

                ctx,

                "Invalid duration."

            )

        if not await self.can_moderate(

            ctx.author,

            member

        ):

            return await self.fail(

                ctx,

                "Cannot moderate."

            )

        until=(

            discord.utils.utcnow()

            +

            timedelta(

                minutes=minutes

            )

        )

        await member.timeout(

            until,

            reason=reason

        )

        await ctx.send(

            embed=self.embed(

                title="Timeout",

                description=f"{member.mention}\n{minutes} minutes"

            )

        )

        await dispatch_log(

            ctx.guild,

            "timeout",

            content=f"{member} timed out",

            user_id=member.id,

            moderator_id=ctx.author.id

        )

    # ==========================================
    # UNTIMEOUT
    # ==========================================

    @commands.hybrid_command()

    async def untimeout(

        self,

        ctx,

        member:discord.Member

    ):

        await member.timeout(

            None

        )

        await ctx.send(

            embed=self.embed(

                description="Timeout removed",

                color=SUCCESS

            )

        )

        await dispatch_log(

            ctx.guild,

            "untimeout",

            content=f"{member} timeout removed",

            user_id=member.id,

            moderator_id=ctx.author.id

        )


async def setup(bot):

    await bot.add_cog(

        Moderation(bot)

    )
