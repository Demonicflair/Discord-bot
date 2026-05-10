import discord
from discord.ext import commands
import aiosqlite
import time

DB_PATH = "bot.db"
DEM_COLOR = 0x2b2d31

class AFK(commands.Cog):
    """
    🌙 Professional AFK System
    Features: Auto-Nickname, Time Formatting, and Multi-server support.
    """
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk (
                    guild_id INTEGER,
                    user_id INTEGER,
                    reason TEXT,
                    since INTEGER,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.commit()

    # =========================
    # TIME FORMATTER
    # =========================
    def get_time_string(self, seconds):
        if seconds < 60:
            return f"{seconds}s"
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        parts = []
        if days > 0: parts.append(f"{days}d")
        if hours > 0: parts.append(f"{hours}h")
        if minutes > 0: parts.append(f"{minutes}m")
        if seconds > 0: parts.append(f"{seconds}s")
        return " ".join(parts)

    # =========================
    # AFK COMMAND
    # =========================
    @commands.hybrid_command(
        name="afk",
        description="Set an away status so others know you are busy."
    )
    async def afk(self, ctx, *, reason: str = "Away from keyboard"):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO afk (guild_id, user_id, reason, since) VALUES (?, ?, ?, ?)",
                (ctx.guild.id, ctx.author.id, reason, int(time.time()))
            )
            await db.commit()

        # Update Nickname
        if not ctx.author.display_name.startswith("[AFK]"):
            try:
                await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")
            except:
                pass # Bot lacks permission or user is owner

        embed = discord.Embed(
            description=f"🌙 {ctx.author.mention}, I've set your AFK: **{reason}**",
            color=DEM_COLOR
        )
        await ctx.send(embed=embed)

    # =========================
    # LISTENERS
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # 1. REMOVE AFK (When the user speaks)
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT reason, since FROM afk WHERE guild_id=? AND user_id=?",
                (message.guild.id, message.author.id)
            ) as cursor:
                data = await cursor.fetchone()

                if data:
                    reason, since = data
                    duration = self.get_time_string(int(time.time()) - since)

                    await db.execute(
                        "DELETE FROM afk WHERE guild_id=? AND user_id=?",
                        (message.guild.id, message.author.id)
                    )
                    await db.commit()

                    # Reset Nickname
                    try:
                        new_nick = message.author.display_name.replace("[AFK] ", "")
                        await message.author.edit(nick=new_nick)
                    except:
                        pass

                    embed = discord.Embed(
                        title="👋 Welcome Back!",
                        description=f"I've removed your AFK status.\nLogged: `{duration}`",
                        color=discord.Color.green()
                    )
                    await message.channel.send(embed=embed, delete_after=10)

        # 2. NOTIFY MENTIONS (When someone pings an AFK user)
        if message.mentions:
            for user in message.mentions:
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute(
                        "SELECT reason, since FROM afk WHERE guild_id=? AND user_id=?",
                        (message.guild.id, user.id)
                    ) as cursor:
                        afk_data = await cursor.fetchone()

                        if afk_data:
                            reason, since = afk_data
                            duration = self.get_time_string(int(time.time()) - since)

                            embed = discord.Embed(
                                description=f"💤 **{user.name}** is currently away.",
                                color=discord.Color.orange()
                            )
                            embed.add_field(name="Reason", value=f"`{reason}`")
                            embed.add_field(name="Since", value=f"<t:{since}:R>")
                            
                            await message.channel.send(embed=embed, delete_after=15)

async def setup(bot):
    await bot.add_cog(AFK(bot))
