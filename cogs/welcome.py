import asyncio
import discord
import aiosqlite

from discord.ext import commands

from utils.config import (
    DB_PATH,
    BRAND_COLOR
)

from utils.dispatch import dispatch_log

from utils.embeds import (
    success_embed,
    error_embed,
    base_embed
)


WELCOME_COLOR = BRAND_COLOR


class Welcome(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

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
                (
                    member.guild.owner.mention
                    if member.guild.owner
                    else "Unknown"
                )

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

            """,(guild_id,)) as cursor:

                return await cursor.fetchone()

    # ======================
    # JOIN
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
            _leave,
            welcome_message,
            _leavemsg,
            autorole,
            use_embed

        ) = data

        text = self.format_message(

            welcome_message
            or "Welcome {user} to {server}",

            member

        )

        if welcome_channel:

            channel = member.guild.get_channel(
                welcome_channel
            )

            if channel:

                try:

                    if use_embed:

                        embed = discord.Embed(

                            description=text,

                            color=WELCOME_COLOR

                        )

                        embed.set_author(

                            name=f"{member} joined",

                            icon_url=member.display_avatar.url

                        )

                        embed.set_thumbnail(

                            url=member.display_avatar.url

                        )

                        embed.set_footer(

                            text=f"Member #{member.guild.member_count}"

                        )

                        await channel.send(
                            embed=embed
                        )

                    else:

                        await channel.send(
                            text
                        )

                except Exception:

                    pass

        # autorole

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
    # LEAVE
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
            _wc,
            leave_channel,
            _wm,
            leave_message,
            _ar,
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

        try:

            if use_embed:

                embed = discord.Embed(

                    description=text,

                    color=discord.Color.red()

                )

                await channel.send(
                    embed=embed
                )

            else:

                await channel.send(
                    text
                )

        except:

            pass

    # ======================
    # GROUP
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

            embed = base_embed(

                title="Welcome System",

                description=(

                    "`/welcome setup`\n"

                    "`/welcome message`\n"

                    "`/welcome leave_message`\n"

                    "`/welcome embeds`\n"

                    "`/welcome test`"

                )

            )

            await ctx.send(
                embed=embed
            )

    # ======================
    # SETUP
    # ======================

    @welcome.command()

    async def setup(

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
                if leave_channel else None,

                None,

                None,

                autorole.id
                if autorole else None,

                1

            ))

            await db.commit()

        await ctx.send(

            embed=success_embed(

                f"Welcome configured\n\n"

                f"Welcome: {welcome_channel.mention}\n"

                f"Leave: {leave_channel.mention if leave_channel else 'None'}\n"

                f"Autorole: {autorole.mention if autorole else 'None'}"

            )

        )

    @welcome.command()

    async def message(
        self,
        ctx,
        *,
        text:str
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(

                """
                UPDATE welcome_settings
                SET welcome_message=?
                WHERE guild_id=?
                """,

                (
                    text,
                    ctx.guild.id
                )

            )

            await db.commit()

        preview = self.format_message(
            text,
            ctx.author
        )

        await ctx.send(

            embed=success_embed(

                f"Updated message\n\nPreview:\n{preview}"

            )

        )

    @welcome.command()

    async def leave_message(
        self,
        ctx,
        *,
        text:str
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(

                """
                UPDATE welcome_settings
                SET leave_message=?
                WHERE guild_id=?
                """,

                (
                    text,
                    ctx.guild.id
                )

            )

            await db.commit()

        await ctx.send(
            embed=success_embed(
                "Leave message updated."
            )
        )

    @welcome.command()

    async def embeds(
        self,
        ctx,
        state:bool
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(

                """
                UPDATE welcome_settings
                SET use_embed=?
                WHERE guild_id=?
                """,

                (
                    int(state),
                    ctx.guild.id
                )

            )

            await db.commit()

        await ctx.send(

            embed=success_embed(

                f"Embeds {'enabled' if state else 'disabled'}"

            )

        )

    @welcome.command()

    async def test(
        self,
        ctx
    ):

        await self.on_member_join(
            ctx.author
        )

        await ctx.send(

            embed=success_embed(
                "Test welcome triggered."
            )

        )


async def setup(bot):

    await bot.add_cog(
        Welcome(bot)
    )
