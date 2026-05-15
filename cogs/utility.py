# cogs/utility.py

import discord
import aiosqlite
import platform
import psutil
import time

from discord.ext import commands

from utils.config import (
    BRAND_COLOR,
    DB_PATH,
    BOT_NAME
)

from utils.dispatch import dispatch_log

# =========================
# UTILITY COG
# =========================
class Utility(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # DATABASE INIT
    # =========================
    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk (
                    user_id INTEGER,
                    guild_id INTEGER,
                    reason TEXT,
                    since INTEGER,
                    PRIMARY KEY(user_id, guild_id)
                )
            """)

            await db.commit()

    # =========================
    # PREMIUM EMBED
    # =========================
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
            text=f"{BOT_NAME} • Premium Utility System"
        )

        return embed

    # =========================
    # TIME FORMATTER
    # =========================
    def format_time(self, seconds):

        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        parts = []

        if days:
            parts.append(f"{days}d")

        if hours:
            parts.append(f"{hours}h")

        if minutes:
            parts.append(f"{minutes}m")

        if seconds:
            parts.append(f"{seconds}s")

        return " ".join(parts)

    # =========================
    # USER INFO
    # =========================
    @commands.hybrid_command(
        name="userinfo",
        description="View detailed information about a user."
    )
    async def userinfo(
        self,
        ctx,
        member: discord.Member = None
    ):

        member = member or ctx.author

        embed = self.dem_embed(
            color=member.color if member.color != discord.Color.default() else BRAND_COLOR
        )

        embed.set_author(
            name=f"{member}",
            icon_url=member.display_avatar.url
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        # =========================
        # BASIC INFO
        # =========================
        embed.add_field(
            name="👤 Username",
            value=f"`{member}`",
            inline=True
        )

        embed.add_field(
            name="🆔 User ID",
            value=f"`{member.id}`",
            inline=True
        )

        embed.add_field(
            name="🤖 Bot",
            value="Yes" if member.bot else "No",
            inline=True
        )

        # =========================
        # ACCOUNT INFO
        # =========================
        embed.add_field(
            name="📅 Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:F>",
            inline=False
        )

        embed.add_field(
            name="📥 Joined Server",
            value=f"<t:{int(member.joined_at.timestamp())}:F>",
            inline=False
        )

        # =========================
        # ROLES
        # =========================
        roles = [
            role.mention
            for role in reversed(member.roles[1:])
        ]

        role_text = (
            " ".join(roles[:15])
            if roles else
            "No roles"
        )

        if len(role_text) > 1024:
            role_text = role_text[:1000] + "..."

        embed.add_field(
            name=f"🎭 Roles [{len(roles)}]",
            value=role_text,
            inline=False
        )

        # =========================
        # EXTRA
        # =========================
        embed.add_field(
            name="🛡️ Highest Role",
            value=member.top_role.mention,
            inline=True
        )

        embed.add_field(
            name="🚀 Boosting",
            value=(
                f"Since <t:{int(member.premium_since.timestamp())}:R>"
                if member.premium_since
                else "No"
            ),
            inline=True
        )

        embed.add_field(
            name="📛 Nickname",
            value=member.nick or "None",
            inline=True
        )

        await ctx.send(embed=embed)

    # =========================
    # SERVER INFO
    # =========================
    @commands.hybrid_command(
        name="serverinfo",
        description="View detailed server information."
    )
    async def serverinfo(self, ctx):

        guild = ctx.guild

        humans = len([
            m for m in guild.members
            if not m.bot
        ])

        bots = guild.member_count - humans

        embed = self.dem_embed(
            title=f"{guild.name} Statistics"
        )

        if guild.icon:
            embed.set_thumbnail(
                url=guild.icon.url
            )

        if guild.banner:
            embed.set_image(
                url=guild.banner.url
            )

        # =========================
        # GENERAL
        # =========================
        embed.add_field(
            name="👑 Owner",
            value=guild.owner.mention,
            inline=True
        )

        embed.add_field(
            name="🆔 Server ID",
            value=f"`{guild.id}`",
            inline=True
        )

        embed.add_field(
            name="📅 Created",
            value=f"<t:{int(guild.created_at.timestamp())}:D>",
            inline=True
        )

        # =========================
        # MEMBERS
        # =========================
        embed.add_field(
            name="👥 Members",
            value=(
                f"Total: `{guild.member_count}`\n"
                f"Humans: `{humans}`\n"
                f"Bots: `{bots}`"
            ),
            inline=True
        )

        # =========================
        # CHANNELS
        # =========================
        embed.add_field(
            name="💬 Channels",
            value=(
                f"Text: `{len(guild.text_channels)}`\n"
                f"Voice: `{len(guild.voice_channels)}`\n"
                f"Categories: `{len(guild.categories)}`"
            ),
            inline=True
        )

        # =========================
        # BOOSTS
        # =========================
        embed.add_field(
            name="🚀 Nitro Boost",
            value=(
                f"Level `{guild.premium_tier}`\n"
                f"Boosts `{guild.premium_subscription_count}`"
            ),
            inline=True
        )

        # =========================
        # SECURITY
        # =========================
        embed.add_field(
            name="🛡️ Security",
            value=(
                f"Verification: `{guild.verification_level}`\n"
                f"MFA Level: `{guild.mfa_level}`"
            ),
            inline=True
        )

        # =========================
        # EXTRA
        # =========================
        embed.add_field(
            name="🎭 Roles",
            value=f"`{len(guild.roles)}`",
            inline=True
        )

        embed.add_field(
            name="😀 Emojis",
            value=f"`{len(guild.emojis)}`",
            inline=True
        )

        embed.add_field(
            name="🌎 Preferred Locale",
            value=f"`{guild.preferred_locale}`",
            inline=True
        )

        await ctx.send(embed=embed)

    # =========================
    # PING
    # =========================
    @commands.hybrid_command(
        name="ping",
        description="Check bot latency and response speed."
    )
    async def ping(self, ctx):

        start = time.perf_counter()

        msg = await ctx.send(
            "📡 Establishing secure connection..."
        )

        end = time.perf_counter()

        message_latency = round(
            (end - start) * 1000
        )

        gateway = round(
            self.bot.latency * 1000
        )

        if gateway <= 100:
            status = "🟢 Excellent"

        elif gateway <= 250:
            status = "🟡 Stable"

        else:
            status = "🔴 High Latency"

        embed = self.dem_embed(
            title="🏓 Connection Statistics"
        )

        embed.description = (
            f"**Gateway Latency**\n"
            f"`{gateway}ms`\n\n"
            f"**Message Response**\n"
            f"`{message_latency}ms`\n\n"
            f"**Status**\n"
            f"{status}"
        )

        await msg.edit(
            content=None,
            embed=embed
        )

    # =========================
    # BOT INFO
    # =========================
    @commands.hybrid_command(
        name="botinfo",
        description="View information about the bot."
    )
    async def botinfo(self, ctx):

        process = psutil.Process()

        ram = round(
            process.memory_info().rss / 1024 / 1024,
            2
        )

        uptime = int(
            time.time() - process.create_time()
        )

        embed = self.dem_embed(
            title=f"{BOT_NAME} Statistics"
        )

        embed.add_field(
            name="🌍 Servers",
            value=f"`{len(self.bot.guilds)}`",
            inline=True
        )

        embed.add_field(
            name="👥 Users",
            value=f"`{len(self.bot.users)}`",
            inline=True
        )

        embed.add_field(
            name="⚡ Commands",
            value=f"`{len(self.bot.commands)}`",
            inline=True
        )

        embed.add_field(
            name="💾 RAM Usage",
            value=f"`{ram} MB`",
            inline=True
        )

        embed.add_field(
            name="🐍 Python",
            value=f"`{platform.python_version()}`",
            inline=True
        )

        embed.add_field(
            name="📚 Discord.py",
            value=f"`{discord.__version__}`",
            inline=True
        )

        embed.add_field(
            name="⏳ Uptime",
            value=f"`{self.format_time(uptime)}`",
            inline=False
        )

        await ctx.send(embed=embed)

    # =========================
    # AVATAR
    # =========================
    @commands.hybrid_command(
        name="avatar",
        description="View a user's avatar."
    )
    async def avatar(
        self,
        ctx,
        member: discord.Member = None
    ):

        member = member or ctx.author

        embed = self.dem_embed(
            title=f"{member}'s Avatar"
        )

        embed.set_image(
            url=member.display_avatar.url
        )

        await ctx.send(embed=embed)

    # =========================
    # AFK COMMAND
    # =========================
    @commands.hybrid_command(
        name="afk",
        description="Set your AFK status."
    )
    async def afk(
        self,
        ctx,
        *,
        reason: str = "Away from keyboard"
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT OR REPLACE INTO afk
                VALUES (?, ?, ?, ?)
                """,
                (
                    ctx.author.id,
                    ctx.guild.id,
                    reason,
                    int(time.time())
                )
            )

            await db.commit()

        # Nickname
        if not ctx.author.display_name.startswith("[AFK]"):

            try:
                await ctx.author.edit(
                    nick=f"[AFK] {ctx.author.display_name}"
                )
            except:
                pass

        embed = self.dem_embed(
            description=(
                f"💤 {ctx.author.mention} is now AFK.\n\n"
                f"**Reason:** {reason}"
            )
        )

        await ctx.send(embed=embed)

    # =========================
    # AFK LISTENER
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):

        if not message.guild:
            return

        if message.author.bot:
            return

        # =========================
        # REMOVE AFK
        # =========================
        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT reason, since
                FROM afk
                WHERE user_id=? AND guild_id=?
                """,
                (
                    message.author.id,
                    message.guild.id
                )
            ) as cursor:

                data = await cursor.fetchone()

                if data:

                    reason, since = data

                    await db.execute(
                        """
                        DELETE FROM afk
                        WHERE user_id=? AND guild_id=?
                        """,
                        (
                            message.author.id,
                            message.guild.id
                        )
                    )

                    await db.commit()

                    try:

                        nick = (
                            message.author.display_name
                            .replace("[AFK] ", "")
                        )

                        await message.author.edit(
                            nick=nick
                        )

                    except:
                        pass

                    duration = self.format_time(
                        int(time.time()) - since
                    )

                    embed = self.dem_embed(
                        title="👋 Welcome Back",
                        description=(
                            f"{message.author.mention}, "
                            f"your AFK has been removed.\n\n"
                            f"**AFK Duration:** `{duration}`"
                        ),
                        color=discord.Color.green()
                    )

                    await message.channel.send(
                        embed=embed,
                        delete_after=8
                    )

        # =========================
        # AFK MENTION ALERT
        # =========================
        for user in message.mentions:

            async with aiosqlite.connect(DB_PATH) as db:

                async with db.execute(
                    """
                    SELECT reason, since
                    FROM afk
                    WHERE user_id=? AND guild_id=?
                    """,
                    (
                        user.id,
                        message.guild.id
                    )
                ) as cursor:

                    afk = await cursor.fetchone()

                    if afk:

                        reason, since = afk

                        embed = self.dem_embed(
                            title="💤 User is AFK",
                            description=(
                                f"{user.mention} is currently away.\n\n"
                                f"**Reason:** {reason}\n"
                                f"**Since:** <t:{since}:R>"
                            ),
                            color=discord.Color.orange()
                        )

                        await message.channel.send(
                            embed=embed,
                            delete_after=10
                        )

        await self.bot.process_commands(message)


# =========================
# LOAD COG
# =========================
async def setup(bot):

    await bot.add_cog(Utility(bot))
