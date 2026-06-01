import math
import random
import time

import discord
import aiosqlite

from discord.ext import commands, tasks

from utils.config import (
    DB_PATH,
    BRAND_COLOR,
    LEVEL_ROLES,
    XP_PER_MESSAGE
)

LEVEL_UP_COLOR = 0xf1c40f
VOICE_REWARD_TIME = 60
MESSAGE_COOLDOWN = 10
PRESTIGE_LEVEL = 100


class Leveling(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.message_cooldowns = {}

        self.voice_xp.start()

    async def cog_unload(self):

        self.voice_xp.cancel()

    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.executescript("""

            CREATE TABLE IF NOT EXISTS levels(

            guild_id INTEGER,
            user_id INTEGER,

            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            prestige INTEGER DEFAULT 0,

            messages INTEGER DEFAULT 0,
            voice_seconds INTEGER DEFAULT 0,

            weekly_xp INTEGER DEFAULT 0,

            rep INTEGER DEFAULT 0,

            bio TEXT DEFAULT '',

            PRIMARY KEY(guild_id,user_id)

            );

            CREATE TABLE IF NOT EXISTS level_blacklist(

            guild_id INTEGER,
            channel_id INTEGER,

            PRIMARY KEY(guild_id,channel_id)

            );

            CREATE TABLE IF NOT EXISTS xp_boosts(

            guild_id INTEGER,
            role_id INTEGER,
            multiplier REAL,

            PRIMARY KEY(guild_id,role_id)

            );

            """)

            await db.commit()

    def calculate_level(self,xp):

        return int(
            0.2 *
            math.sqrt(max(xp,0))
        )

    def xp_needed(self,level):

        return int(
            (level/0.2)**2
        )

    async def get_data(
        self,
        guild_id,
        user_id
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""

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

            """,(guild_id,user_id)) as cur:

                data=await cur.fetchone()

            if data:

                return data

            await db.execute("""

            INSERT INTO levels

            (guild_id,user_id)

            VALUES (?,?)

            """,(guild_id,user_id))

            await db.commit()

        return (
            0,0,0,0,0,0,0,""
        )

    async def multiplier(
        self,
        member
    ):

        multi=1.0

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""

            SELECT role_id,multiplier

            FROM xp_boosts

            WHERE guild_id=?

            """,(member.guild.id,)) as cur:

                rows=await cur.fetchall()

        for role_id,m in rows:

            role=member.guild.get_role(
                role_id
            )

            if role and role in member.roles:

                multi+=m

        return multi

    async def add_xp(
        self,
        member,
        amount
    ):

        data=await self.get_data(
            member.guild.id,
            member.id
        )

        xp,level,prestige,messages,voice,weekly,rep,bio=data

        amount=int(
            amount*
            await self.multiplier(member)
        )

        xp+=amount
        weekly+=amount

        new_level=self.calculate_level(
            xp
        )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            UPDATE levels

            SET

            xp=?,
            level=?,
            weekly_xp=?

            WHERE guild_id=?
            AND user_id=?

            """,(

            xp,
            new_level,
            weekly,

            member.guild.id,
            member.id

            ))

            await db.commit()

        if new_level>level:

            await self.level_up(
                member,
                new_level
            )

    async def level_up(
        self,
        member,
        level
    ):

        embed=discord.Embed(

            title="Level Up!",

            description=(
                f"{member.mention} reached "
                f"Level {level}"
            ),

            color=LEVEL_UP_COLOR

        )

        try:

            await member.send(
                embed=embed
            )

        except:
            pass

        for req,role_name in LEVEL_ROLES.items():

            if level>=req:

                role=discord.utils.get(

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

        if level>=PRESTIGE_LEVEL:

            async with aiosqlite.connect(DB_PATH) as db:

                await db.execute("""

                UPDATE levels

                SET

                prestige=prestige+1,
                xp=0,
                level=0

                WHERE guild_id=?
                AND user_id=?

                """,(

                member.guild.id,
                member.id

                ))

                await db.commit()

    @commands.Cog.listener()
    async def on_message(
        self,
        message
    ):

        if not message.guild:
            return

        if message.author.bot:
            return

        key=(
            message.guild.id,
            message.author.id
        )

        now=time.time()

        if key in self.message_cooldowns:

            if now-self.message_cooldowns[key]<MESSAGE_COOLDOWN:

                return

        self.message_cooldowns[key]=now

        if len(message.content)<4:

            return

        xp_gain=random.randint(

            max(
                1,
                XP_PER_MESSAGE-5
            ),

            XP_PER_MESSAGE+10

        )

        await self.add_xp(

            message.author,

            xp_gain

        )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            UPDATE levels

            SET messages=messages+1

            WHERE guild_id=?
            AND user_id=?

            """,(

            message.guild.id,
            message.author.id

            ))

            await db.commit()

    @tasks.loop(minutes=1)
    async def voice_xp(self):

        for guild in self.bot.guilds:

            for vc in guild.voice_channels:

                for member in vc.members:

                    if member.bot:

                        continue

                    await self.add_xp(
                        member,
                        20
                    )

    @voice_xp.before_loop
    async def before_voice(self):

        await self.bot.wait_until_ready()

    @commands.hybrid_command()
    async def rank(
        self,
        ctx,
        member:discord.Member=None
    ):

        member=member or ctx.author

        xp,level,prestige,messages,voice,weekly,rep,bio=await self.get_data(

            ctx.guild.id,

            member.id

        )

        needed=self.xp_needed(
            level+1
        )

        progress=min(

            round(
                (xp/needed)*100,
                1
            ),

            100

        )

        embed=discord.Embed(

            title=f"{member.name}'s Rank",

            color=BRAND_COLOR

        )

        embed.description=(

            f"Level: `{level}`\n"

            f"XP: `{xp}/{needed}`\n"

            f"Progress: `{progress}%`"

        )

        await ctx.send(
            embed=embed
        )

    @commands.hybrid_command()
    async def setbio(
        self,
        ctx,
        *,
        text:str
    ):

        if len(text)>300:

            return await ctx.send(
                "Bio too long."
            )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            UPDATE levels

            SET bio=?

            WHERE guild_id=?
            AND user_id=?

            """,(

            text,

            ctx.guild.id,

            ctx.author.id

            ))

            await db.commit()

        await ctx.send(
            "Updated bio."
        )


async def setup(bot):

    await bot.add_cog(
        Leveling(bot)
    )
