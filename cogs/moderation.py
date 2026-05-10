import discord
from discord.ext import commands
from discord import app_commands
import datetime
import time
import aiosqlite
from utils.dispatch import dispatch_log # Using our central log sender

DB_PATH = "data.db"
MOD_COLOR = 0x2b2d31

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # 🛡️ INTERNAL HIERARCHY CHECK
    # =========================
    async def is_trusted(self, moderator, target):
        """Prevents staff from moderating people above or equal to them."""
        if moderator.guild.owner == moderator: return True
        if target.top_role >= moderator.top_role: return False
        return True

    # =========================
    # 🔨 KICK COMMAND
    # =========================
    @commands.hybrid_command(name="kick", description="👢 Kick a member from the server.")
    @commands.has_permissions(kick_members=True)
    @app_commands.describe(member="The user to kick", reason="Reason for the kick")
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if not await self.is_trusted(ctx.author, member):
            return await ctx.send("❌ You cannot kick someone with a higher or equal role.")

        await member.kick(reason=f"By {ctx.author}: {reason}")
        
        embed = discord.Embed(description=f"✅ **{member}** was kicked | {reason}", color=discord.Color.orange())
        await ctx.send(embed=embed)

        # Send to central logging
        await dispatch_log(ctx.guild, "kick", f"**Member:** {member}\n**Mod:** {ctx.author}\n**Reason:** {reason}")

    # =========================
    # 🚫 BAN COMMAND
    # =========================
    @commands.hybrid_command(name="ban", description="🔨 Permanently ban a member.")
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(member="The user to ban", reason="Reason for the ban", delete_days="Clear message history")
    async def ban(self, ctx, member: discord.Member, delete_days: int = 0, *, reason: str = "No reason provided"):
        if not await self.is_trusted(ctx.author, member):
            return await ctx.send("❌ You cannot ban someone with a higher or equal role.")

        await member.ban(reason=f"By {ctx.author}: {reason}", delete_message_days=delete_days)
        
        embed = discord.Embed(description=f"✅ **{member}** was banned | {reason}", color=discord.Color.red())
        await ctx.send(embed=embed)

        await dispatch_log(ctx.guild, "ban", f"**Member:** {member}\n**Mod:** {ctx.author}\n**Reason:** {reason}")

    # =========================
    # ⚠️ WARNING SYSTEM
    # =========================
    @commands.hybrid_command(name="warn", description="⚠️ Add a warning to a member.")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        if member.bot: return await ctx.send("❌ You cannot warn bots.")
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO warnings (user_id, guild_id, reason, moderator_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                (member.id, ctx.guild.id, reason, ctx.author.id, int(time.time()))
            )
            await db.commit()

        embed = discord.Embed(description=f"⚠️ **{member.mention}** has been warned | {reason}", color=MOD_COLOR)
        await ctx.send(embed=embed)
        
        await dispatch_log(ctx.guild, "warn", f"**Member:** {member}\n**Mod:** {ctx.author}\n**Reason:** {reason}")

    # =========================
    # 🧹 PURGE (Clear Messages)
    # =========================
    @commands.hybrid_command(name="clear", description="🧹 Delete a specific amount of messages.")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        if amount > 100:
            return await ctx.send("❌ You can only clear 100 messages at a time.", delete_after=5)
        
        deleted = await ctx.channel.purge(limit=amount + 1) # +1 to include the command itself
        await ctx.send(f"🗑️ Deleted `{len(deleted)-1}` messages.", delete_after=3)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
                             
