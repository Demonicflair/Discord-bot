import time
import discord

from discord.ext import commands
from discord import app_commands

from utils.database import get_db
from utils.config import BRAND_COLOR
from utils.dispatch import dispatch_log


AFK_CACHE = {}


class AFK(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # LOAD AFK TABLE
    # =========================

    async def cog_load(self):

        db = await get_db()

        await db.execute("""

        CREATE TABLE IF NOT EXISTS afk(

            user_id INTEGER,
            guild_id INTEGER,
            reason TEXT,
            since INTEGER,

            PRIMARY KEY(
                user_id,
                guild_id
            )

        )

        """)

        await db.commit()
        await db.close()

    # =========================
    # FORMAT TIME
    # =========================

    def format_duration(self, seconds):

        minutes, seconds = divmod(
            seconds,
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

        parts = []

        if days:
            parts.append(f"{days}d")

        if hours:
            parts.append(f"{hours}h")

        if minutes:
            parts.append(f"{minutes}m")

        if seconds:
            parts.append(f"{seconds}s")

        return " ".join(parts) or "0s"

    # =========================
    # AFK COMMAND
    # =========================

    @commands.hybrid_command(
        name="afk",
        description="Set AFK status."
    )

    @app_commands.describe(
        reason="AFK reason"
    )

    async def afk(
        self,
        ctx,
        *,
        reason: str = "Away From Keyboard"
    ):

        now = int(
            time.time()
        )

        db = await get_db()

        await db.execute("""

        INSERT OR REPLACE INTO afk(

            user_id,
            guild_id,
            reason,
            since

        )

        VALUES (?, ?, ?, ?)

        """, (

            ctx.author.id,
            ctx.guild.id,
            reason,
            now

        ))

        await db.commit()

        await db.close()

        AFK_CACHE[(

            ctx.guild.id,
            ctx.author.id

        )] = {

            "reason": reason,
            "since": now

        }

        if not ctx.author.display_name.startswith(
            "[AFK]"
        ):

            try:

                await ctx.author.edit(

                    nick=f"[AFK] {ctx.author.display_name[:24]}"

                )

            except discord.HTTPException:

                pass

        embed = discord.Embed(

            description=(
                f"🌙 {ctx.author.mention} is now AFK\n"
                f"Reason: `{reason}`"
            ),

            color=BRAND_COLOR

        )

        await ctx.send(
            embed=embed
        )

        await dispatch_log(

            ctx.guild,

            "afk",

            content=(
                f"User: {ctx.author}\n"
                f"Reason: {reason}"
            ),

            user_id=ctx.author.id

        )

    # =========================
    # MESSAGE LISTENER
    # =========================

    @commands.Cog.listener()

    async def on_message(
        self,
        message
    ):

        if not message.guild:

            return

        if message.author.bot:

            return

        guild_id = message.guild.id

        user_id = message.author.id

        key = (

            guild_id,
            user_id

        )

        # =========================
        # REMOVE AFK
        # =========================

        if key in AFK_CACHE:

            data = AFK_CACHE.pop(
                key
            )

            duration = self.format_duration(

                int(time.time())

                - data["since"]

            )

            db = await get_db()

            await db.execute("""

            DELETE FROM afk

            WHERE guild_id=?
            AND user_id=?

            """, (

                guild_id,
                user_id

            ))

            await db.commit()

            await db.close()

            if message.author.display_name.startswith(
                "[AFK]"
            ):

                try:

                    nickname = (

                        message.author.display_name

                        .replace(
                            "[AFK] ",
                            ""
                        )

                    )

                    await message.author.edit(

                        nick=nickname[:32]

                    )

                except discord.HTTPException:

                    pass

            embed = discord.Embed(

                title="👋 Welcome Back",

                description=(
                    f"AFK removed after "
                    f"`{duration}`"
                ),

                color=discord.Color.green()

            )

            await message.channel.send(

                embed=embed,

                delete_after=10

            )

            await dispatch_log(

                message.guild,

                "afk_remove",

                content=(
                    f"User: {message.author}\n"
                    f"Duration: {duration}"
                ),

                user_id=user_id

            )

        # =========================
        # MENTION CHECK
        # =========================

        if not message.mentions:

            return

        for member in message.mentions:

            if member.bot:

                continue

            mention_key = (

                guild_id,
                member.id

            )

            if mention_key not in AFK_CACHE:

                db = await get_db()

                async with db.execute("""

                SELECT reason,since

                FROM afk

                WHERE guild_id=?
                AND user_id=?

                """, (

                    guild_id,
                    member.id

                )) as cursor:

                    data = await cursor.fetchone()

                await db.close()

                if data:

                    AFK_CACHE[mention_key] = {

                        "reason": data[0],

                        "since": data[1]

                    }

            afk_data = AFK_CACHE.get(
                mention_key
            )

            if not afk_data:

                continue

            duration = self.format_duration(

                int(time.time())

                - afk_data["since"]

            )

            embed = discord.Embed(

                description=(

                    f"💤 {member.mention} is AFK\n"

                    f"Reason: `{afk_data['reason']}`\n"

                    f"Since: `{duration}` ago"

                ),

                color=discord.Color.orange()

            )

            await message.channel.send(

                embed=embed,

                delete_after=8

            )


async def setup(bot):

    await bot.add_cog(
        AFK(bot)
    )
