import re
import time
import asyncio
import datetime
import discord

from discord.ext import commands, tasks

from utils.dispatch import dispatch_log
from utils.database import get_db
from utils.config import (

    SCAM_PATTERN,
    BAD_WORDS,
    ANTI_LINK

)

# ==========================
# SCAM PATTERNS
# ==========================

SCAM_PATTERNS=[

    r"free.*nitro",

    r"nitro.*free",

    r"steam.*gift",

    r"claim.*reward",

    r"discord.*gift",

    r"free.*robux",

    r"cheap.*nitro",

    r"airdrop",

    r"crypto.*reward"

]

if isinstance(SCAM_PATTERN,str):

    SCAM_PATTERNS.append(
        SCAM_PATTERN
    )

COMPILED_SCAMS=[

    re.compile(

        pattern,

        re.IGNORECASE

    )

    for pattern in SCAM_PATTERNS

]


class SecurityAI(commands.Cog):

    def __init__(self,bot):

        self.bot=bot

        self.heat_levels={}

        self.message_cache={}

        self.settings_cache={}

        self.clean_heat.start()

    def cog_unload(self):

        self.clean_heat.cancel()

    async def get_security_setting(

        self,

        guild_id,

        feature

    ):

        key=(guild_id,feature)

        if key in self.settings_cache:

            return self.settings_cache[key]

        db=await get_db()

        try:

            cursor=await db.execute(

                """

                SELECT enabled

                FROM settings

                WHERE guild_id=?

                AND feature=?

                """,

                (

                    guild_id,

                    feature

                )

            )

            row=await cursor.fetchone()

            await cursor.close()

        finally:

            await db.close()

        value=True if row is None else bool(

            row["enabled"]

        )

        self.settings_cache[key]=value

        return value

    async def add_heat(

        self,

        message,

        amount,

        reason

    ):

        if message.author.guild_permissions.manage_messages:

            return

        key=(

            message.guild.id,

            message.author.id

        )

        current=self.heat_levels.get(

            key,

            0

        )

        current+=amount

        self.heat_levels[key]=current

        if current>=10:

            try:

                await message.author.ban(

                    reason=reason

                )

            except:

                pass

            return

        elif current>=6:

            try:

                await message.author.timeout(

                    discord.utils.utcnow()

                    +

                    datetime.timedelta(

                        hours=1

                    ),

                    reason=reason

                )

            except:

                pass

    @tasks.loop(

        minutes=30

    )

    async def clean_heat(self):

        remove=[]

        for k in list(

            self.heat_levels

        ):

            self.heat_levels[k]-=1

            if self.heat_levels[k]<=0:

                remove.append(k)

        for k in remove:

            self.heat_levels.pop(

                k,

                None

            )

        self.message_cache.clear()

    @commands.Cog.listener()

    async def on_message(

        self,

        message

    ):

        if (

            not message.guild

            or

            message.author.bot

        ):

            return

        content=message.content.lower()

        if await self.get_security_setting(

            message.guild.id,

            "badword_filter"

        ):

            for word in BAD_WORDS:

                if word.lower() in content:

                    await message.delete()

                    await self.add_heat(

                        message,

                        2,

                        "Bad Words"

                    )

                    return

        if await self.get_security_setting(

            message.guild.id,

            "scam_protection"

        ):

            for pattern in COMPILED_SCAMS:

                if pattern.search(content):

                    await message.delete()

                    await self.add_heat(

                        message,

                        5,

                        "Scam"

                    )

                    return

        if (

            ANTI_LINK

            and

            "http" in content

        ):

            if not message.author.guild_permissions.manage_messages:

                await message.delete()

                await self.add_heat(

                    message,

                    3,

                    "Links"

                )

                return

async def setup(bot):

    await bot.add_cog(

        SecurityAI(bot)

    )
