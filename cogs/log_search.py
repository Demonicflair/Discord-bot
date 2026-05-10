
import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import datetime

# Using your unified DB path
DB_PATH = "bot.db"
BRAND_COLOR = 0x2b2d31

class LogSearch(commands.Cog):
    """
    🔍 Investigation Suite
    Allows staff to query the database for moderation history and security flags.
    """
    def __init__(self, bot):
        self.bot = bot

    def search_embed(self, title, description=None):
        embed = discord.Embed(title=title, description=description, color=BRAND_COLOR)
        embed.set_footer(text="Dem Intelligence System • History Lookup")
        return embed

    # =========================
    # 🔍 SEARCH BY USER
    # =========================
    @commands.hybrid_command(
        name="history", 
        description="🔎 View the full moderation history of a specific member."
    )
    @app_commands.describe(user="The user to investigate")
    @commands.has_permissions(manage_messages=True)
    async def history(self, ctx, user: discord.User):
        await ctx.defer()
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Fetching warnings from your database module's table
            async with db.execute(
                "SELECT COUNT(*) FROM warnings WHERE user_id=? AND guild_id=?", 
                (user.id, ctx.guild.id)
            ) as cur:
                warn_res = await cur.fetchone()
                warn_count = warn_res[0] if warn_res else 0

            # Fetching AI Security Scores (from security.py logic)
            # Note: This assumes we added a persistent 'scores' table as discussed
            async with db.execute(
                "SELECT enabled FROM settings WHERE guild_id=? AND feature='security'", 
                (ctx.guild.id,)
            ) as cur:
                sec_status = await cur.fetchone()
                sec_enabled = "🟢 Active" if sec_status and sec_status[0] == 1 else "🔴 Inactive"

        embed = self.search_embed(f"Security Report: {user.name}")
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(name="⚠️ Warnings", value=f"`{warn_count}` total warnings", inline=True)
        embed.add_field(name="🛡️ AI Protection", value=sec_enabled, inline=True)
        embed.add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)

        # Integration with your specific database logging system
        # This part queries the 'logs' table if you are saving strings there
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT type, reason, timestamp FROM logs WHERE user_id=? AND guild_id=? ORDER BY timestamp DESC LIMIT 5",
                (user.id, ctx.guild.id)
            ) as cur:
                recent_actions = await cur.fetchall()

        if recent_actions:
            history_text = ""
            for act_type, reason, ts in recent_actions:
                history_text += f"• **{act_type.upper()}**: {reason} (<t:{ts}:R>)\n"
            embed.add_field(name="📋 Recent Actions", value=history_text, inline=False)
        else:
            embed.add_field(name="📋 Recent Actions", value="No recorded incidents found.", inline=False)

        await ctx.send(embed=embed)

    # =========================
    # 📊 GUILD SNAPSHOT
    # =========================
    @commands.hybrid_command(
        name="mod_stats", 
        description="📊 View total moderation statistics for this server."
    )
    @commands.has_permissions(administrator=True)
    async def mod_stats(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=?", (ctx.guild.id,)) as cur:
                total_warns = (await cur.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM ticket_blacklist WHERE guild_id=?", (ctx.guild.id,)) as cur:
                blacklisted = (await cur.fetchone())[0]

        embed = self.search_embed("Server Moderation Overview")
        embed.add_field(name="⚠️ Total Warns", value=f"`{total_warns}`", inline=True)
        embed.add_field(name="🚫 Ticket Bans", value=f"`{blacklisted}`", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LogSearch(bot))
