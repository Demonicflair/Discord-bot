# afk.py

import discord
from discord.ext import commands
import sqlite3
import time

# =========================
# DATABASE
# =========================
db = sqlite3.connect("afk.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS afk(
    guild_id INTEGER,
    user_id INTEGER,
    reason TEXT,
    since INTEGER
)
""")

db.commit()

# =========================
# COG
# =========================
class AFK(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # SET AFK
    # =========================
    @commands.hybrid_command(
        name="afk",
        help="Set your AFK status.",
        extras={
            "example": "!afk Sleeping",
            "tips": "Mentioned users will see your AFK reason."
        }
    )
    async def afk(
        self,
        ctx,
        *,
        reason="AFK"
    ):
        """Set AFK."""

        cursor.execute(
            """
            DELETE FROM afk
            WHERE guild_id=? AND user_id=?
            """,
            (ctx.guild.id, ctx.author.id)
        )

        cursor.execute(
            """
            INSERT INTO afk VALUES (?, ?, ?, ?)
            """,
            (
                ctx.guild.id,
                ctx.author.id,
                reason,
                int(time.time())
            )
        )

        db.commit()

        embed = discord.Embed(
            title="🌙 AFK Enabled",
            description=f"Reason: **{reason}**",
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

    # =========================
    # MESSAGE LISTENER
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot or not message.guild:
            return

        # =========================
        # REMOVE AFK
        # =========================
        cursor.execute(
            """
            SELECT reason, since FROM afk
            WHERE guild_id=? AND user_id=?
            """,
            (message.guild.id, message.author.id)
        )

        data = cursor.fetchone()

        if data:

            cursor.execute(
                """
                DELETE FROM afk
                WHERE guild_id=? AND user_id=?
                """,
                (message.guild.id, message.author.id)
            )

            db.commit()

            duration = int(time.time()) - data[1]

            embed = discord.Embed(
                title="👋 Welcome Back",
                description=(
                    f"You were AFK for "
                    f"`{duration}` seconds."
                ),
                color=discord.Color.green()
            )

            await message.channel.send(
                embed=embed
            )

        # =========================
        # AFK MENTION
        # =========================
        for user in message.mentions:

            cursor.execute(
                """
                SELECT reason, since FROM afk
                WHERE guild_id=? AND user_id=?
                """,
                (message.guild.id, user.id)
            )

            afk = cursor.fetchone()

            if afk:

                reason = afk[0]
                duration = int(time.time()) - afk[1]

                embed = discord.Embed(
                    title="🌙 User AFK",
                    description=(
                        f"{user.mention} is AFK\n\n"
                        f"📝 Reason: **{reason}**\n"
                        f"⏰ Since: `{duration}` seconds ago"
                    ),
                    color=discord.Color.orange()
                )

                await message.channel.send(
                    embed=embed
                )

        await self.bot.process_commands(message)


# =========================
# SETUP
# =========================
async def setup(bot):

    await bot.add_cog(AFK(bot))
