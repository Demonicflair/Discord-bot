import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio

from utils.dispatch import dispatch_log

DB_PATH = "data.db"

WELCOME_COLOR = 0x2b2d31


class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # PLACEHOLDER ENGINE
    # =========================
    def format_message(
        self,
        text: str,
        member: discord.Member
    ):

        count = member.guild.member_count

        suffix = (
            "th"
            if 11 <= count % 100 <= 13
            else {
                1: "st",
                2: "nd",
                3: "rd"
            }.get(count % 10, "th")
        )

        replacements = {
            "{user}": member.mention,
            "{user_name}": member.name,
            "{display_name}": member.display_name,
            "{server}": member.guild.name,
            "{member_count}": str(count),
            "{count_suffix}": suffix,
            "{owner}": member.guild.owner.mention
        }

        for key, value in replacements.items():
            text = text.replace(key, value)

        return text

    # =========================
    # MEMBER JOIN
    # =========================
    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT *
                FROM welcome_settings
                WHERE guild_id=?
                """,
                (member.guild.id,)
            ) as cursor:

                data = await cursor.fetchone()

        if not data:
            return

        (
            guild_id,
            welcome_channel,
            leave_channel,
            welcome_message,
            leave_message,
            autorole,
            use_embed
        ) = data

        # =========================
        # SEND WELCOME
        # =========================
        if welcome_channel:

            channel = member.guild.get_channel(
                welcome_channel
            )

            if channel:

                message = self.format_message(
                    welcome_message
                    or "Welcome {user} to {server}!",
                    member
                )

                try:

                    if use_embed:

                        embed = discord.Embed(
                            description=message,
                            color=WELCOME_COLOR
                        )

                        embed.set_author(
                            name=f"{member} joined the server",
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

                        await channel.send(message)

                except Exception as e:
                    print(f"[WELCOME ERROR] {e}")

        # =========================
        # AUTO ROLE
        # =========================
        if autorole:

            await asyncio.sleep(2)

            role = member.guild.get_role(
                autorole
            )

            if role:

                try:

                    await member.add_roles(
                        role,
                        reason="Dem Auto Role"
                    )

                except Exception as e:
                    print(f"[AUTOROLE ERROR] {e}")

        # =========================
        # LOG JOIN
        # =========================
        await dispatch_log(
            member.guild,
            "member_join",
            content=f"📥 {member.mention} joined the server.",
            user_id=member.id
        )

    # =========================
    # MEMBER LEAVE
    # =========================
    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT *
                FROM welcome_settings
                WHERE guild_id=?
                """,
                (member.guild.id,)
            ) as cursor:

                data = await cursor.fetchone()

        if not data:
            return

        (
            guild_id,
            welcome_channel,
            leave_channel,
            welcome_message,
            leave_message,
            autorole,
            use_embed
        ) = data

        if not leave_channel:
            return

        channel = member.guild.get_channel(
            leave_channel
        )

        if not channel:
            return

        message = self.format_message(
            leave_message
            or "{user_name} left the server.",
            member
        )

        try:

            if use_embed:

                embed = discord.Embed(
                    description=message,
                    color=discord.Color.red()
                )

                embed.set_author(
                    name=f"{member} left the server",
                    icon_url=member.display_avatar.url
                )

                await channel.send(embed=embed)

            else:

                await channel.send(message)

        except Exception as e:
            print(f"[LEAVE ERROR] {e}")

    # =========================
    # WELCOME GROUP
    # =========================
    @commands.hybrid_group(
        name="welcome",
        description="🏠 Welcome system settings."
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcome(self, ctx):

        if ctx.invoked_subcommand is None:

            await ctx.send(
                "Use `/welcome setup` to configure the system."
            )

    # =========================
    # SETUP
    # =========================
    @welcome.command(
        name="setup",
        description="Configure welcome system."
    )
    async def setup_welcome(
        self,
        ctx,
        welcome_channel: discord.TextChannel,
        leave_channel: discord.TextChannel = None,
        autorole: discord.Role = None
    ):

        role_id = autorole.id if autorole else None
        leave_id = leave_channel.id if leave_channel else None

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT OR REPLACE INTO welcome_settings
                (
                    guild_id,
                    welcome_channel,
                    leave_channel,
                    autorole,
                    use_embed
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ctx.guild.id,
                    welcome_channel.id,
                    leave_id,
                    role_id,
                    1
                )
            )

            await db.commit()

        await ctx.send(
            f"✅ Welcome system configured.\n"
            f"📥 Welcome: {welcome_channel.mention}\n"
            f"📤 Leave: {leave_channel.mention if leave_channel else 'Not Set'}\n"
            f"🎭 Auto Role: {autorole.mention if autorole else 'None'}"
        )

    # =========================
    # SET WELCOME MESSAGE
    # =========================
    @welcome.command(
        name="message",
        description="Set custom welcome message."
    )
    async def set_message(
        self,
        ctx,
        *,
        text: str
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
            f"✅ Welcome message updated.\n\n"
            f"Preview:\n{preview}"
        )

    # =========================
    # SET LEAVE MESSAGE
    # =========================
    @welcome.command(
        name="leave_message",
        description="Set custom leave message."
    )
    async def set_leave_message(
        self,
        ctx,
        *,
        text: str
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
            "✅ Leave message updated."
        )

    # =========================
    # TOGGLE EMBEDS
    # =========================
    @welcome.command(
        name="embeds",
        description="Enable or disable embeds."
    )
    async def toggle_embeds(
        self,
        ctx,
        state: bool
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
            f"✅ Welcome embeds {'enabled' if state else 'disabled'}."
        )

    # =========================
    # TEST MESSAGE
    # =========================
    @welcome.command(
        name="test",
        description="Send a test welcome message."
    )
    async def test_welcome(
        self,
        ctx
    ):

        self.bot.dispatch(
            "member_join",
            ctx.author
        )

        await ctx.send(
            "✅ Test welcome triggered."
        )


async def setup(bot):
    await bot.add_cog(Welcome(bot))
