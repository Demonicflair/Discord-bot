import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import aiosqlite
import database  # Your async database module
from utils.logger import save_log

# Professional Aesthetic
BRAND_COLOR = 0x2b2d31 
DB_PATH = "bot.db"

class Moderation(commands.Cog):
    """
    🔨 Elite Moderation Suite
    Features: Hybrid Commands, Trusted Admin System, and Auto-Punish Toggle.
    """
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Initializes settings and trusted admin tables asynchronously."""
        async with aiosqlite.connect(DB_PATH) as db:
            # Auto-Punish Settings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS mod_settings (
                    guild_id INTEGER PRIMARY KEY, 
                    autopunish_enabled INTEGER
                )
            """)
            # Trusted Admins (Selected by Owner)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trusted_admins (
                    guild_id INTEGER, 
                    user_id INTEGER, 
                    PRIMARY KEY(guild_id, user_id)
                )
            """)
            await db.commit()

    # =========================
    # INTERNAL HELPERS
    # =========================
    async def is_trusted(self, guild: discord.Guild, user: discord.Member) -> bool:
        """Checks if a user is the owner or in the trusted admin list."""
        if user.id == guild.owner_id:
            return True
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT 1 FROM trusted_admins WHERE guild_id=? AND user_id=?", 
                (guild.id, user.id)
            ) as cur:
                return await cur.fetchone() is not None

    def check_hierarchy(self, ctx, target: discord.Member):
        """Checks if the moderator has a higher role than the target."""
        if target.id == ctx.author.id:
            return "You cannot punish yourself."
        if target.id == ctx.guild.owner_id:
            return "You cannot punish the Server Owner."
        if target.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return "This user has a higher or equal role than you."
        if target.top_role >= ctx.guild.me.top_role:
            return "This user's role is higher than mine."
        return None

    # =========================
    # TRUST MANAGEMENT (Owner Only)
    # =========================
    @commands.hybrid_command(
        name="trust_admin", 
        description="👑 (Owner Only) Add a trusted admin to manage auto-punish settings."
    )
    @app_commands.describe(user="The administrator to trust")
    async def trust_admin(self, ctx, user: discord.Member):
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ Only the **Server Owner** can manage trusted admins.", ephemeral=True)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO trusted_admins VALUES (?, ?)", (ctx.guild.id, user.id))
            await db.commit()
        
        await ctx.send(embed=discord.Embed(description=f"✅ {user.mention} is now a **Trusted Admin**.", color=discord.Color.green()))

    @commands.hybrid_command(
        name="untrust_admin", 
        description="👑 (Owner Only) Remove a user from the trusted admin list."
    )
    @app_commands.describe(user="The admin to remove trust from")
    async def untrust_admin(self, ctx, user: discord.Member):
        if ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ Only the **Server Owner** can manage trusted admins.", ephemeral=True)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM trusted_admins WHERE guild_id=? AND user_id=?", (ctx.guild.id, user.id))
            await db.commit()
        
        await ctx.send(embed=discord.Embed(description=f"❌ {user.mention} removed from Trusted Admins.", color=discord.Color.red()))

    # =========================
    # SETTINGS TOGGLE (Owner & Trusted)
    # =========================
    @commands.hybrid_command(
        name="autopunish_toggle", 
        description="🛡️ Toggle the auto-punishment system (Owner/Trusted only)."
    )
    @app_commands.describe(status="Enable or Disable punishments")
    @app_commands.choices(status=[
        app_commands.Choice(name="Enabled", value=1),
        app_commands.Choice(name="Disabled", value=0)
    ])
    async def autopunish_toggle(self, ctx, status: app_commands.Choice[int]):
        if not await self.is_trusted(ctx.guild, ctx.author):
            return await ctx.send("❌ You are not a **Trusted Admin** or the Server Owner.", ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO mod_settings VALUES (?, ?)", (ctx.guild.id, status.value))
            await db.commit()

        state = "ENABLED" if status.value == 1 else "DISABLED"
        await ctx.send(embed=discord.Embed(
            description=f"⚙️ Auto-punishment has been **{state}** by {ctx.author.mention}.",
            color=discord.Color.blue()
        ))

    # =========================
    # CORE MODERATION COMMANDS
    # =========================
    @commands.hybrid_command(name="warn", description="⚠️ Warn a member and track their history.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(member="Member to warn", reason="Reason for warning")
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        error = self.check_hierarchy(ctx, member)
        if error: return await ctx.send(f"❌ {error}", ephemeral=True)

        warn_count = await database.add_warn(member.id, ctx.guild.id)
        
        await ctx.send(embed=discord.Embed(
            description=f"⚠️ {member.mention} warned. Total: `{warn_count}`\n**Reason:** {reason}",
            color=discord.Color.yellow()
        ))

        # Check Auto-Punish Authorization
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT autopunish_enabled FROM mod_settings WHERE guild_id=?", (ctx.guild.id,)) as cursor:
                res = await cursor.fetchone()
                if res and res[0] == 0:
                    return # Stop here if disabled

        # Proceed with Punishments
        if warn_count == 3:
            await member.timeout(datetime.timedelta(hours=1), reason="3 Warnings Auto-Punish")
            await ctx.send(f"🔇 {member.mention} timed out (1h) - 3 warns reached.")
        elif warn_count >= 5:
            await member.ban(reason="5 Warnings Auto-Punish")
            await ctx.send(f"🔨 {member.mention} banned - 5 warns reached.")

    @commands.hybrid_command(name="ban", description="🔨 Ban a member.")
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(member="User to ban", reason="Reason")
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        error = self.check_hierarchy(ctx, member)
        if error: return await ctx.send(f"❌ {error}", ephemeral=True)

        await member.ban(reason=f"Mod: {ctx.author} | {reason}")
        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
        embed.add_field(name="Target", value=f"{member.mention} (`{member.id}`)")
        embed.add_field(name="Moderator", value=ctx.author.mention)
        await ctx.send(embed=embed)
        save_log(ctx.guild.id, member.id, "ban", f"Banned by {ctx.author}: {reason}")

    @commands.hybrid_command(name="clear", description="🧹 Bulk delete messages.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(amount="Number of messages to delete")
    async def clear(self, ctx, amount: int):
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"✅ Cleared `{len(deleted)-1}` messages.", delete_after=3)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
