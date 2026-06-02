import math
import random
import time

import discord

from discord.ext import commands, tasks

from utils.database import get_db
from utils.config import (
    BRAND_COLOR,
    LEVEL_ROLES,
    XP_PER_MESSAGE
)

LEVEL_UP_COLOR = 0xf1c40f

MESSAGE_COOLDOWN = 10

VOICE_XP = 20

PRESTIGE_LEVEL = 100


class Leveling(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.message_cooldowns = {}

        self.voice_xp.start()

    async def cog_unload(self):

        self.voice_xp.cancel()

    # ==================================
    # LEVEL FORMULAS
    # ==================================

    def calculate_level(self, xp):

        return int(
            0.2 *
            math.sqrt(
                max(
                    xp,
                    0
                )
            )
        )

    def xp_needed(self, level):

        return int(
            (level / 0.2) ** 2
        )

    # ==================================
    # GET USER DATA
    # ==================================

    async def get_data(
        self,
        guild_id,
        user_id
    ):

        async with await get_db() as db:

            async with db.execute(
                """
                SELECT
                xp,
                level,
                prestige,
                messages,
                voice_seconds,
                weekly_xp,
                rep,
                bio

                FROM levels

                WHERE guild_id=?
                AND user_id=?
                """,
                (
                    guild_id,
                    user_id
                )
            ) as cur:

                data = await cur.fetchone()

            if data:

                return data

            await db.execute(
                """
                INSERT INTO levels
                (guild_id,user_id)
                VALUES (?,?)
                """,
                (
                    guild_id,
                    user_id
                )
            )

            await db.commit()

        return (
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            ""
        )

    # ==================================
    # XP MULTIPLIER
    # ==================================

    async def multiplier(
        self,
        member
    ):

        multi = 1.0

        async with await get_db() as db:

            async with db.execute(
                """
                SELECT role_id,multiplier

                FROM xp_boosts

                WHERE guild_id=?
                """,
                (
                    member.guild.id,
                )
            ) as cur:

                rows = await cur.fetchall()

        for role_id, m in rows:

            role = member.guild.get_role(
                role_id
            )

            if role and role in member.roles:

                multi += m

        return multi

    # ==================================
    # ADD XP
    # ==================================

    async def add_xp(
        self,
        member,
        amount
    ):

        data = await self.get_data(
            member.guild.id,
            member.id
        )

        xp, level, prestige, messages, voice, weekly, rep, bio = data

        amount = int(
            amount *
            await self.multiplier(
                member
            )
        )

        xp += amount

        weekly += amount

        new_level = self.calculate_level(
            xp
        )

        async with await get_db() as db:

            await db.execute(
                """
                UPDATE levels

                SET

                xp=?,
                level=?,
                weekly_xp=?

                WHERE guild_id=?
                AND user_id=?
                """,
                (
                    xp,
                    new_level,
                    weekly,
                    member.guild.id,
                    member.id
                )
            )

            await db.commit()

        if new_level > level:

            await self.level_up(
                member,
                new_level
            )

    # ==================================
    # LEVEL UP
    # ==================================

    async def level_up(
        self,
        member,
        level
    ):

        embed = discord.Embed(

            title="Level Up",

            description=(
                f"{member.mention}\n"
                f"You reached **Level {level}**"
            ),

            color=LEVEL_UP_COLOR

        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        try:

            await member.send(
                embed=embed
            )

        except:

            pass

        for req, role_name in LEVEL_ROLES.items():

            if level >= req:

                role = discord.utils.get(

                    member.guild.roles,

                    name=role_name

                )

                if role:

                    try:

                        await member.add_roles(
                            role
                        )

                    except:

                        pass

        if level >= PRESTIGE_LEVEL:

            async with await get_db() as db:

                await db.execute(
                    """
                    UPDATE levels

                    SET

                    prestige=prestige+1,
                    xp=0,
                    level=0

                    WHERE guild_id=?
                    AND user_id=?
                    """,
                    (
                        member.guild.id,
                        member.id
                    )
                )

                await db.commit()

    # ==================================
    # MESSAGE XP
    # ==================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message
    ):

        if not message.guild:

            return

        if message.author.bot:

            return

        key = (

            message.guild.id,

            message.author.id

        )

        now = time.time()

        if key in self.message_cooldowns:

            if (

                now -
                self.message_cooldowns[key]

            ) < MESSAGE_COOLDOWN:

                return

        self.message_cooldowns[key] = now

        if len(message.content) < 4:

            return

        xp = random.randint(

            max(
                1,
                XP_PER_MESSAGE - 5
            ),

            XP_PER_MESSAGE + 10

        )

        await self.add_xp(

            message.author,

            xp

        )

        async with await get_db() as db:

            await db.execute(
                """
                UPDATE levels

                SET messages=messages+1

                WHERE guild_id=?
                AND user_id=?
                """,
                (
                    message.guild.id,
                    message.author.id
                )
            )

            await db.commit()

    # ==================================
    # VOICE XP
    # ==================================

    @tasks.loop(
        minutes=1
    )
    async def voice_xp(self):

        for guild in self.bot.guilds:

            for vc in guild.voice_channels:

                for member in vc.members:

                    if member.bot:

                        continue

                    await self.add_xp(

                        member,

                        VOICE_XP

                    )

    @voice_xp.before_loop
    async def before_voice(self):

        await self.bot.wait_until_ready()

    # ==================================
    # RANK
    # ==================================

    @commands.hybrid_command()

    async def rank(

        self,

        ctx,

        member: discord.Member=None

    ):

        member = member or ctx.author

        xp, level, prestige, messages, voice, weekly, rep, bio = await self.get_data(

            ctx.guild.id,

            member.id

        )

        needed = self.xp_needed(
            level + 1
        )

        progress = min(

            round(
                (xp / needed) * 100,
                1
            ),

            100

        )

        embed = discord.Embed(

            title=f"{member.display_name}",

            color=BRAND_COLOR

        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.description=(

            f"**Level:** `{level}`\n"

            f"**XP:** `{xp}/{needed}`\n"

            f"**Progress:** `{progress}%`\n"

            f"**Prestige:** `{prestige}`"

        )

        await ctx.send(
            embed=embed
        )


async def setup(bot):

    await bot.add_cog(
        Leveling(bot)
    )
