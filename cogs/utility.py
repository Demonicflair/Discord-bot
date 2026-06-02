# cogs/utility.py

import discord
import platform
import psutil
import time

from discord.ext import commands

from utils.config import (
    BRAND_COLOR,
    BOT_NAME
)

from utils.database import get_db

from utils.dispatch import dispatch_log


class Utility(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # ===================================
    # EMBEDS
    # ===================================

    def dem_embed(
        self,
        title=None,
        description=None,
        color=BRAND_COLOR
    ):

        embed = discord.Embed(

            title=title,

            description=description,

            color=color,

            timestamp=discord.utils.utcnow()

        )

        embed.set_footer(

            text=f"{BOT_NAME} • Utility System"

        )

        return embed

    # ===================================
    # FORMAT TIME
    # ===================================

    def format_time(
        self,
        seconds
    ):

        minutes, seconds = divmod(
            int(seconds),
            60
        )

        hours, minutes = divmod(
            minutes,
            60
        )

        days, hours = divmod(
            hours,
            24
        )

        parts=[]

        if days:
            parts.append(f"{days}d")

        if hours:
            parts.append(f"{hours}h")

        if minutes:
            parts.append(f"{minutes}m")

        if seconds:
            parts.append(f"{seconds}s")

        return " ".join(parts) or "0s"

    # ===================================
    # USER INFO
    # ===================================

    @commands.hybrid_command()

    async def userinfo(
        self,
        ctx,
        member:discord.Member=None
    ):

        member=member or ctx.author

        embed=self.dem_embed(

            color=member.color
            if member.color.value
            else BRAND_COLOR

        )

        embed.set_author(

            name=str(member),

            icon_url=member.display_avatar.url

        )

        embed.set_thumbnail(

            url=member.display_avatar.url

        )

        roles=[

            r.mention

            for r in reversed(
                member.roles[1:]
            )

        ]

        embed.add_field(

            name="User",

            value=(
                f"ID: `{member.id}`\n"
                f"Bot: `{member.bot}`"
            )

        )

        embed.add_field(

            name="Created",

            value=f"<t:{int(member.created_at.timestamp())}:F>",

            inline=False

        )

        embed.add_field(

            name="Joined",

            value=f"<t:{int(member.joined_at.timestamp())}:F>",

            inline=False

        )

        embed.add_field(

            name=f"Roles [{len(roles)}]",

            value=" ".join(
                roles[:15]
            ) or "None",

            inline=False

        )

        embed.add_field(

            name="Highest Role",

            value=member.top_role.mention

        )

        embed.add_field(

            name="Nickname",

            value=member.nick or "None"

        )

        await ctx.send(
            embed=embed
        )

    # ===================================
    # PING
    # ===================================

    @commands.hybrid_command()

    async def ping(
        self,
        ctx
    ):

        start=time.perf_counter()

        msg=await ctx.send(
            "Pinging..."
        )

        end=time.perf_counter()

        message_latency=round(

            (end-start)*1000

        )

        gateway=round(

            self.bot.latency*1000

        )

        embed=self.dem_embed(

            title="Pong"

        )

        embed.description=(

            f"Gateway: `{gateway}ms`\n"

            f"Message: `{message_latency}ms`"

        )

        await msg.edit(

            content=None,

            embed=embed

        )

    # ===================================
    # BOT INFO
    # ===================================

    @commands.hybrid_command()

    async def botinfo(
        self,
        ctx
    ):

        process=psutil.Process()

        uptime=int(

            time.time()

            -

            process.create_time()

        )

        ram=round(

            process.memory_info().rss

            /1024/1024,

            2

        )

        embed=self.dem_embed(

            title=f"{BOT_NAME}"

        )

        embed.add_field(

            name="Servers",

            value=str(
                len(self.bot.guilds)
            )

        )

        embed.add_field(

            name="Users",

            value=str(
                len(self.bot.users)
            )

        )

        embed.add_field(

            name="RAM",

            value=f"{ram}MB"

        )

        embed.add_field(

            name="Python",

            value=platform.python_version()

        )

        embed.add_field(

            name="Uptime",

            value=self.format_time(
                uptime
            ),

            inline=False

        )

        await ctx.send(
            embed=embed
        )

    # ===================================
    # AFK
    # ===================================

    @commands.hybrid_command()

    async def afk(
        self,
        ctx,
        *,
        reason="Away"
    ):

        async with await get_db() as db:

            await db.execute(

                """
                INSERT OR REPLACE INTO afk
                VALUES(?,?,?,?)
                """,

                (

                    ctx.author.id,

                    ctx.guild.id,

                    reason,

                    int(time.time())

                )

            )

            await db.commit()

        try:

            if not ctx.author.display_name.startswith("[AFK]"):

                await ctx.author.edit(

                    nick=f"[AFK] {ctx.author.display_name}"

                )

        except:

            pass

        await ctx.send(

            embed=self.dem_embed(

                description=f"{ctx.author.mention} is now AFK\nReason: {reason}"

            )

        )

    # ===================================
    # AFK LISTENER
    # ===================================

    @commands.Cog.listener()

    async def on_message(
        self,
        message
    ):

        if not message.guild:

            return

        if message.author.bot:

            return

        async with await get_db() as db:

            async with db.execute(

                """

                SELECT reason,since

                FROM afk

                WHERE user_id=?
                AND guild_id=?

                """,

                (

                    message.author.id,

                    message.guild.id

                )

            ) as cursor:

                afk=await cursor.fetchone()

            if afk:

                reason,since=afk

                await db.execute(

                    """

                    DELETE FROM afk

                    WHERE user_id=?
                    AND guild_id=?

                    """,

                    (

                        message.author.id,

                        message.guild.id

                    )

                )

                await db.commit()

                duration=self.format_time(

                    time.time()-since

                )

                await message.channel.send(

                    embed=self.dem_embed(

                        title="Welcome Back",

                        description=f"AFK removed after `{duration}`",

                        color=discord.Color.green()

                    ),

                    delete_after=8

                )

            for user in message.mentions:

                async with db.execute(

                    """

                    SELECT reason,since

                    FROM afk

                    WHERE user_id=?
                    AND guild_id=?

                    """,

                    (

                        user.id,

                        message.guild.id

                    )

                ) as cur:

                    data=await cur.fetchone()

                if data:

                    reason,since=data

                    await message.channel.send(

                        embed=self.dem_embed(

                            title="User AFK",

                            description=(

                                f"{user.mention}\n"

                                f"Reason: {reason}\n"

                                f"Since: <t:{since}:R>"

                            )

                        ),

                        delete_after=10

                    )


async def setup(bot):

    await bot.add_cog(

        Utility(bot)

    )
