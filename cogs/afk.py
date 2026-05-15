import discord
from discord.ext import commands
from discord import app_commands
import time

from utils.database import get_db
from utils.config import BRAND_COLOR
from utils.dispatch import dispatch_log

AFK_CACHE = {}


# =========================
# AFK SYSTEM
# =========================
class AFK(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # TIME FORMATTER
    # =========================
    def format_duration(self, seconds):

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

        return " ".join(parts) or "0s"

    # =========================
    # AFK COMMAND
    # =========================
    @commands.hybrid_command(
        name="afk",
        description="Set your AFK status."
    )
    @app_commands.describe(
        reason="Reason for going AFK"
    )
    async def afk(self, ctx, *, reason: str = "Away From Keyboard"):

        db = await get_db()

        await db.execute("""
            INSERT OR REPLACE INTO afk
            (user_id, guild_id, reason, since)
            VALUES (?, ?, ?, ?)
        """, (
            ctx.author.id,
            ctx.guild.id,
            reason,
            int(time.time())
        ))

        await db.commit()
        await db.close()

        AFK_CACHE[(ctx.guild.id, ctx.author.id)] = {
            "reason": reason,
            "since": int(time.time())
        }

        # =========================
        # AUTO NICKNAME
        # =========================
        if not ctx.author.display_name.startswith("[AFK]"):

            try:
                await ctx.author.edit(
                    nick=f"[AFK] {ctx.author.display_name[:24]}"
                )

            except:
                pass

        embed = discord.Embed(
            description=f"🌙 {ctx.author.mention} is now AFK.\nReason: `{reason}`",
            color=BRAND_COLOR
        )

        await ctx.send(embed=embed)

        # =========================
        # LOGGING
        # =========================
        await dispatch_log(
            ctx.guild,
            "afk",
            f"**User:** {ctx.author}\n**Reason:** {reason}",
            user_id=ctx.author.id
        )

    # =========================
    # MESSAGE LISTENER
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):

        if not message.guild:
            return

        if message.author.bot:
            return

        key = (message.guild.id, message.author.id)

        # =========================
        # REMOVE AFK
        # =========================
        if key in AFK_CACHE:

            data = AFK_CACHE[key]

            duration = self.format_duration(
                int(time.time()) - data["since"]
            )

            db = await get_db()

            await db.execute("""
                DELETE FROM afk
                WHERE guild_id=? AND user_id=?
            """, (
                message.guild.id,
                message.author.id
            ))

            await db.commit()
            await db.close()

            del AFK_CACHE[key]

            # Restore nickname
            if message.author.display_name.startswith("[AFK]"):

                try:
                    new_name = message.author.display_name.replace("[AFK] ", "")

                    await message.author.edit(
                        nick=new_name[:32]
                    )

                except:
                    pass

            embed = discord.Embed(
                title="👋 Welcome Back",
                description=f"AFK removed after `{duration}`",
                color=discord.Color.green()
            )

            await message.channel.send(
                embed=embed,
                delete_after=10
            )

            await dispatch_log(
                message.guild,
                "afk_remove",
                f"**User:** {message.author}\n**Duration:** {duration}",
                user_id=message.author.id
            )

        # =========================
        # AFK MENTION ALERTS
        # =========================
        if not message.mentions:
            return

        for member in message.mentions:

            if member.bot:
                continue

            mention_key = (message.guild.id, member.id)

            # Cache miss -> load from DB
            if mention_key not in AFK_CACHE:

                db = await get_db()

                async with db.execute("""
                    SELECT reason, since
                    FROM afk
                    WHERE guild_id=? AND user_id=?
                """, (
                    message.guild.id,
                    member.id
                )) as cursor:

                    data = await cursor.fetchone()

                await db.close()

                if data:

                    AFK_CACHE[mention_key] = {
                        "reason": data[0],
                        "since": data[1]
                    }

            # Still not AFK
            if mention_key not in AFK_CACHE:
                continue

            afk_data = AFK_CACHE[mention_key]

            duration = self.format_duration(
                int(time.time()) - afk_data["since"]
            )

            embed = discord.Embed(
                description=(
                    f"💤 {member.mention} is currently AFK.\n"
                    f"Reason: `{afk_data['reason']}`\n"
                    f"Since: `{duration}` ago"
                ),
                color=discord.Color.orange()
            )

            await message.channel.send(
                embed=embed,
                delete_after=8
            )


# =========================
# LOAD COG
# =========================
async def setup(bot):

    await bot.add_cog(AFK(bot))
