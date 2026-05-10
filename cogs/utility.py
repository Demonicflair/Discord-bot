import discord
from discord.ext import commands
from discord import app_commands
import platform
import psutil
import aiosqlite
import time

# Using your existing logger
from utils.logger import get_logs, save_log, is_log_enabled

DB_PATH = "bot.db"
# A slightly softer dark color for that "Premium" look
DEM_COLOR = 0x2b2d31 

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk (
                    user_id INTEGER,
                    guild_id INTEGER,
                    reason TEXT,
                    since INTEGER,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            await db.commit()

    # =========================
    # AESTHETIC EMBED HELPER
    # =========================
    def dem_embed(self, title=None, description=None, color=DEM_COLOR):
        embed = discord.Embed(title=title, description=description, color=color)
        # Using a blank character in the footer for a "thin" look
        embed.set_footer(text="Dem System • " + discord.utils.utcnow().strftime("%H:%M"))
        return embed

    # =========================
    # 👤 USER INFO (Overhauled)
    # =========================
    @commands.hybrid_command(name="userinfo", description="Display a member's profile card.")
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        
        embed = self.dem_embed(color=member.color)
        embed.set_author(name=f"{member.name}'s Profile", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Identity Row
        embed.add_field(name="🆔 User ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="🎨 Nickname", value=f"`{member.nick or 'None'}`", inline=True)
        embed.add_field(name="🤖 Bot", value=f"`{'Yes' if member.bot else 'No'}`", inline=True)

        # Dates Row (Using Discord Timestamps)
        embed.add_field(name="🗓️ Registered", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="📥 Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        embed.add_field(name="🛡️ Top Role", value=member.top_role.mention, inline=True)

        # Roles List (Cleanly formatted)
        roles = [r.mention for r in member.roles[1:]][::-1]
        role_str = " ".join(roles[:8]) + ("..." if len(roles) > 8 else "") if roles else "No roles"
        embed.add_field(name=f"🎭 Roles [{len(roles)}]", value=role_str, inline=False)

        await ctx.send(embed=embed)

    # =========================
    # 🌐 SERVER INFO (Overhauled)
    # =========================
    @commands.hybrid_command(name="serverinfo", description="Detailed statistics of this guild.")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        embed = self.dem_embed(title=f"Server Statistics: {guild.name}")
        
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        if guild.banner: embed.set_image(url=guild.banner.url)

        # Basic Stats Grid
        embed.add_field(name="👑 Owner", value=f"{guild.owner.mention}", inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="💎 Boosts", value=f"`Level {guild.premium_tier}` ({guild.premium_subscription_count} boosts)", inline=True)

        # Member Breakdown
        humans = len([m for m in guild.members if not m.bot])
        bots = guild.member_count - humans
        embed.add_field(name="👥 Members", value=f"Total: `{guild.member_count}`\nHumans: `{humans}`\nBots: `{bots}`", inline=True)

        # Channels Breakdown
        embed.add_field(name="💬 Channels", value=f"Text: `{len(guild.text_channels)}`\nVoice: `{len(guild.voice_channels)}`\nCategories: `{len(guild.categories)}`", inline=True)
        
        # Roles Count
        embed.add_field(name="🎭 Security", value=f"Roles: `{len(guild.roles)}`\nEmojis: `{len(guild.emojis)}`", inline=True)

        await ctx.send(embed=embed)

    # =========================
    # 🏓 PING (Ultra Professional)
    # =========================
    @commands.hybrid_command(name="ping", description="Test Dem's connection latency.")
    async def ping(self, ctx):
        api_lat = round(self.bot.latency * 1000)
        
        # Calculate Message Latency
        start = time.perf_counter()
        msg = await ctx.send("📡 *Establishing secure connection...*")
        end = time.perf_counter()
        msg_lat = round((end - start) * 1000)

        embed = self.dem_embed(title="🏓 Connection Latency")
        
        # Color coding based on speed
        status = "🟢 Excellent" if api_lat < 100 else "🟡 Stable" if api_lat < 250 else "🔴 High Latency"
        
        embed.description = (
            f"**Gateway:** `{api_lat}ms`\n"
            f"**Rest API:** `{msg_lat}ms`\n"
            f"**Current Status:** {status}"
        )
        
        await msg.edit(content=None, embed=embed)

    # =========================
    # 💤 AFK SYSTEM (Refined)
    # =========================
    @commands.hybrid_command(name="afk", description="Leave a message for when you are offline.")
    async def afk(self, ctx, *, reason: str = "Away from keyboard"):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO afk VALUES (?, ?, ?, ?)", 
                           (ctx.author.id, ctx.guild.id, reason, int(time.time())))
            await db.commit()

        # Update nickname to include [AFK]
        if not ctx.author.display_name.startswith("[AFK]"):
            try: await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")
            except: pass

        embed = self.dem_embed(description=f"💤 {ctx.author.mention}, you are now AFK.\n**Reason:** {reason}")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return

        # 1. REMOVE AFK
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT reason FROM afk WHERE user_id=? AND guild_id=?", 
                                (message.author.id, message.guild.id)) as cursor:
                if await cursor.fetchone():
                    await db.execute("DELETE FROM afk WHERE user_id=? AND guild_id=?", 
                                   (message.author.id, message.guild.id))
                    await db.commit()
                    
                    try: await message.author.edit(nick=message.author.display_name.replace("[AFK] ", ""))
                    except: pass
                    
                    embed = self.dem_embed(description=f"👋 Welcome back {message.author.mention}! Your AFK has been removed.", color=discord.Color.green())
                    await message.channel.send(embed=embed, delete_after=5)

        # 2. CHECK PINGS
        for user in message.mentions:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT reason, since FROM afk WHERE user_id=? AND guild_id=?", 
                                    (user.id, message.guild.id)) as cursor:
                    data = await cursor.fetchone()
                    if data:
                        embed = self.dem_embed(title="💤 User is Currently AFK", color=discord.Color.orange())
                        embed.description = f"{user.mention} is away: **{data[0]}**\n<t:{data[1]}:R>"
                        await message.channel.send(embed=embed, delete_after=10)

async def setup(bot):
    await bot.add_cog(Utility(bot))
