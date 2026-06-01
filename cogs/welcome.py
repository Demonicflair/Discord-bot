import asyncio
import discord
import aiosqlite

from discord.ext import commands

from utils.database import DB_PATH
from utils.config import BRAND_COLOR
from utils.dispatch import dispatch_log
from utils.embeds import (
    success_embed,
    error_embed,
    base_embed
)


class Welcome(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            CREATE TABLE IF NOT EXISTS welcome_settings(

                guild_id INTEGER PRIMARY KEY,

                welcome_channel INTEGER,

                leave_channel INTEGER,

                welcome_message TEXT,

                leave_message TEXT,

                autorole INTEGER,

                use_embed INTEGER DEFAULT 1

            )

            """)

            await db.commit()

    # ======================
    # PLACEHOLDERS
    # ======================

    def format_message(
        self,
        text,
        member
    ):

        count = member.guild.member_count

        suffix = (

            "th"

            if 11 <= count % 100 <= 13

            else {

                1:"st",
                2:"nd",
                3:"rd"

            }.get(
                count % 10,
                "th"
            )

        )

        owner = (
            member.guild.owner.mention
            if member.guild.owner
            else "Unknown"
        )

        replacements = {

            "{user}":
                member.mention,

            "{user_name}":
                member.name,

            "{display_name}":
                member.display_name,

            "{server}":
                member.guild.name,

            "{member_count}":
                str(count),

            "{count_suffix}":
                suffix,

            "{owner}":
                owner

        }

        for k,v in replacements.items():

            text = text.replace(
                k,
                str(v)
            )

        return text

    async def get_settings(
        self,
        guild_id
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""

            SELECT

            welcome_channel,
            leave_channel,
            welcome_message,
            leave_message,
            autorole,
            use_embed

            FROM welcome_settings

            WHERE guild_id=?

            """,(
                guild_id,
            )) as cursor:

                return await cursor.fetchone()

    # ======================
    # MEMBER JOIN
    # ======================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member
    ):

        data = await self.get_settings(
            member.guild.id
        )

        if not data:
            return

        (
            welcome_channel,
            leave_channel,
            welcome_message,
            leave_message,
            autorole,
            use_embed
        ) = data

        if welcome_channel:

            channel = member.guild.get_channel(
                welcome_channel
            )

            if channel:

                text = self.format_message(

                    welcome_message
                    or "Welcome {user} to {server}",

                    member

                )

                try:

                    if use_embed:

                        embed = base_embed(

                            description=text

                        )

                        embed.set_thumbnail(

                            url=member.display_avatar.url

                        )

                        await channel.send(
                            embed=embed
                        )

                    else:

                        await channel.send(
                            text
                        )

                except Exception as e:

                    print(
                        f"[WELCOME] {e}"
                    )

        if autorole:

            role = member.guild.get_role(
                autorole
            )

            if role:

                try:

                    await asyncio.sleep(2)

                    await member.add_roles(
                        role,
                        reason="Auto Role"
                    )

                except:

                    pass

        await dispatch_log(

            member.guild,

            "member_join",

            content=f"{member} joined",

            user_id=member.id

        )

    # ======================
    # MEMBER LEAVE
    # ======================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member
    ):

        data = await self.get_settings(
            member.guild.id
        )

        if not data:
            return

        (
            _,
            leave_channel,
            _,
            leave_message,
            _,
            use_embed

        ) = data

        if not leave_channel:
            return

        channel = member.guild.get_channel(
            leave_channel
        )

        if not channel:
            return

        text = self.format_message(

            leave_message
            or "{user_name} left.",

            member

        )

        if use_embed:

            embed = base_embed(
                description=text
            )

            await channel.send(
                embed=embed
            )

        else:

            await channel.send(
                text
            )

    # ======================
    # COMMAND GROUP
    # ======================

    @commands.hybrid_group(
        name="welcome"
    )

    @commands.has_permissions(
        administrator=True
    )

    async def welcome(
        self,
        ctx
    ):

        if ctx.invoked_subcommand is None:

            await ctx.send(

                embed=base_embed(

                    description=(
                        "/welcome setup\n"
                        "/welcome message\n"
                        "/welcome leave_message\n"
                        "/welcome embeds\n"
                        "/welcome test"
                    )

                )

            )

    @welcome.command(
        name="setup"
    )

    async def setup_welcome(

        self,

        ctx,

        welcome_channel:discord.TextChannel,

        leave_channel:discord.TextChannel=None,

        autorole:discord.Role=None

    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            INSERT OR REPLACE INTO
            welcome_settings

            VALUES(?,?,?,?,?,?,?)

            """,(

                ctx.guild.id,

                welcome_channel.id,

                leave_channel.id
                if leave_channel
                else None,

                None,

                None,

                autorole.id
                if autorole
                else None,

                1

            ))

            await db.commit()

        await ctx.send(

            embed=success_embed(
                "Welcome configured."
            )

        )

    @welcome.command(
        name="message"
    )

    async def message(

        self,

        ctx,

        *,

        text:str

    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            UPDATE welcome_settings

            SET welcome_message=?

            WHERE guild_id=?

            """,(
                text,
                ctx.guild.id
            ))

            await db.commit()

        await ctx.send(

            embed=success_embed(
                "Welcome message updated."
            )

        )

    @welcome.command(
        name="leave_message"
    )

    async def leave_message(

        self,

        ctx,

        *,

        text:str

    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            UPDATE welcome_settings

            SET leave_message=?

            WHERE guild_id=?

            """,(
                text,
                ctx.guild.id
            ))

            await db.commit()

        await ctx.send(

            embed=success_embed(
                "Leave message updated."
            )

        )

    @welcome.command(
        name="embeds"
    )

    async def embeds(

        self,

        ctx,

        state:bool

    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            UPDATE welcome_settings

            SET use_embed=?

            WHERE guild_id=?

            """,(
                int(state),
                ctx.guild.id
            ))

            await db.commit()

        await ctx.send(

            embed=success_embed(
                "Updated embed setting."
            )

        )

    @welcome.command(
        name="test"
    )

    async def test(

        self,
        ctx

    ):

        await self.on_member_join(
            ctx.author
        )

        await ctx.send(

            embed=success_embed(
                "Test welcome sent."
            )

        )


async def setup(bot):

    await bot.add_cog(

        Welcome(bot)

    )
