import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB_PATH = "data.db"

BRAND_COLOR = 0x2b2d31


class LogSearch(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # EMBED HELPER
    # =========================
    def build_embed(self, title, description=None):

        embed = discord.Embed(
            title=title,
            description=description,
            color=BRAND_COLOR
        )

        embed.set_footer(
            text="Dem Intelligence System"
        )

        return embed

    # =========================
    # USER HISTORY
    # =========================
    @commands.hybrid_command(
        name="history",
        description="🔎 View a member's moderation history."
    )
    @app_commands.describe(
        user="The user to investigate"
    )
    @commands.has_permissions(
        manage_messages=True
    )
    async def history(
        self,
        ctx,
        user: discord.User
    ):

        await ctx.defer()

        async with aiosqlite.connect(DB_PATH) as db:

            # =========================
            # WARN COUNT
            # =========================
            async with db.execute(
                """
                SELECT COUNT(*)
                FROM warnings
                WHERE user_id=? AND guild_id=?
                """,
                (user.id, ctx.guild.id)
            ) as cursor:

                result = await cursor.fetchone()
                warn_count = result[0] if result else 0

            # =========================
            # SECURITY SCORE
            # =========================
            async with db.execute(
                """
                SELECT score
                FROM security_scores
                WHERE user_id=? AND guild_id=?
                """,
                (user.id, ctx.guild.id)
            ) as cursor:

                result = await cursor.fetchone()
                security_score = result[0] if result else 0

            # =========================
            # RECENT LOGS
            # =========================
            async with db.execute(
                """
                SELECT type, content, timestamp
                FROM logs_data
                WHERE user_id=? AND guild_id=?
                ORDER BY case_id DESC
                LIMIT 5
                """,
                (user.id, ctx.guild.id)
            ) as cursor:

                recent_logs = await cursor.fetchall()

        # =========================
        # BUILD EMBED
        # =========================
        embed = self.build_embed(
            f"📁 History for {user}"
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.add_field(
            name="⚠️ Warnings",
            value=f"`{warn_count}`",
            inline=True
        )

        embed.add_field(
            name="🛡️ Security Score",
            value=f"`{security_score}`",
            inline=True
        )

        embed.add_field(
            name="🆔 User ID",
            value=f"`{user.id}`",
            inline=True
        )

        # =========================
        # RECENT ACTIONS
        # =========================
        if recent_logs:

            history_text = ""

            for log_type, content, timestamp in recent_logs:

                history_text += (
                    f"• **{log_type.upper()}**\n"
                    f"{content[:100]}\n\n"
                )

            embed.add_field(
                name="📋 Recent Actions",
                value=history_text[:1024],
                inline=False
            )

        else:

            embed.add_field(
                name="📋 Recent Actions",
                value="No moderation history found.",
                inline=False
            )

        await ctx.send(embed=embed)

    # =========================
    # MOD STATS
    # =========================
    @commands.hybrid_command(
        name="modstats",
        description="📊 View server moderation statistics."
    )
    @commands.has_permissions(
        administrator=True
    )
    async def modstats(self, ctx):

        async with aiosqlite.connect(DB_PATH) as db:

            # Total warnings
            async with db.execute(
                """
                SELECT COUNT(*)
                FROM warnings
                WHERE guild_id=?
                """,
                (ctx.guild.id,)
            ) as cursor:

                total_warns = (
                    await cursor.fetchone()
                )[0]

            # Ticket blacklist
            async with db.execute(
                """
                SELECT COUNT(*)
                FROM ticket_blacklist
                WHERE guild_id=?
                """,
                (ctx.guild.id,)
            ) as cursor:

                blacklisted = (
                    await cursor.fetchone()
                )[0]

            # Total cases
            async with db.execute(
                """
                SELECT COUNT(*)
                FROM logs_data
                WHERE guild_id=?
                """,
                (ctx.guild.id,)
            ) as cursor:

                total_cases = (
                    await cursor.fetchone()
                )[0]

        embed = self.build_embed(
            "📊 Server Moderation Overview"
        )

        embed.add_field(
            name="⚠️ Total Warnings",
            value=f"`{total_warns}`",
            inline=True
        )

        embed.add_field(
            name="🚫 Ticket Blacklists",
            value=f"`{blacklisted}`",
            inline=True
        )

        embed.add_field(
            name="📁 Logged Cases",
            value=f"`{total_cases}`",
            inline=True
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LogSearch(bot))
