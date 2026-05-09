import discord
from discord.ext import commands
from discord import app_commands
import datetime
import database  # Our lightning-fast async DB
from utils.logger import get_logs, save_log, is_log_enabled

# Brand Color for Elite look
BRAND_COLOR = 0x2b2d31 

class Moderation(commands.Cog):
    """
    🔨 Advanced Moderation Suite
    Includes Auto-punish, Timeouts, and modern Embed UI.
    """
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # HELPERS (The "Famous Bot" Secret)
    # =========================
    def check_hierarchy(self, ctx, target: discord.Member):
        """Checks if the moderator can actually punish the target."""
        if target == ctx.author:
            return "You cannot punish yourself."
        if target == ctx.guild.owner:
            return "You cannot punish the Server Owner."
        if target.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return "This user has a higher or equal role than you."
        if target.top_role >= ctx.guild.me.top_role:
            return "This user's role is higher than mine."
        return None

    # =========================
    # 🔨 BAN (Upgraded)
    # =========================
    @commands.hybrid_command(name="ban", description="🔨 Ban a member from the server.")
    @commands.has_permissions(ban_members=True)
    @app_commands.describe(member="The user to ban", reason="Reason for the ban")
    async def ban(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        error = self.check_hierarchy(ctx, member)
        if error:
            return await ctx.send(embed=discord.Embed(description=f"❌ {error}", color=discord.Color.red()), ephemeral=True)

        try:
            await member.ban(reason=f"Mod: {ctx.author} | Reason: {reason}")
            
            embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red(), timestamp=discord.utils.utcnow())
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Target", value=f"{member.mention}\n`{member.id}`", inline=True)
            embed.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Server: {ctx.guild.name}")

            await ctx.send(embed=embed)
            save_log(ctx.guild.id, member.id, "ban", f"Banned by {ctx.author}: {reason}")
        except Exception as e:
            await ctx.send(f"❌ Failed to ban: {e}")

    # =========================
    # ⚠️ WARN & AUTO-PUNISH (Pro Feature)
    # =========================
    @commands.hybrid_command(name="warn", description="⚠️ Warn a member and track their history.")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        error = self.check_hierarchy(ctx, member)
        if error:
            return await ctx.send(f"❌ {error}", ephemeral=True)

        # Using our async database to increment warns
        warn_count = await database.add_warn(member.id, ctx.guild.id)

        embed = discord.Embed(
            title="⚠️ Infraction Logged",
            description=f"{member.mention} has been warned.\n**Total Warnings:** `{warn_count}`",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Reason", value=reason)
        await ctx.send(embed=embed)

        # --- AUTO PUNISH LOGIC ---
        if warn_count == 3:
            await member.timeout(datetime.timedelta(hours=1), reason="3 Warnings Auto-Punish")
            await ctx.send(f"🔇 {member.mention} has been timed out for 1 hour due to 3 warnings.")
        elif warn_count >= 5:
            await member.kick(reason="5 Warnings Auto-Punish")
            await ctx.send(f"👢 {member.mention} has been kicked for reaching 5 warnings.")

    # =========================
    # 🧹 PURGE (New Commands)
    # =========================
    @commands.hybrid_command(name="clear", description="🧹 Bulk delete messages in a channel.")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        if amount > 100:
            return await ctx.send("❌ I can only delete up to 100 messages at a time.", ephemeral=True)
        
        deleted = await ctx.channel.purge(limit=amount + 1) # +1 to include the command itself
        
        msg = await ctx.send(embed=discord.Embed(
            description=f"✅ Successfully cleared `{len(deleted)-1}` messages.",
            color=discord.Color.green()
        ))
        await asyncio.sleep(3)
        await msg.delete()

    # =========================
    # 🔇 TIMEOUT (Modernized)
    # =========================
    @commands.hybrid_command(name="timeout", description="🔇 Timeout a member for a specific duration.")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int, *, reason: str = "No reason"):
        error = self.check_hierarchy(ctx, member)
        if error: return await ctx.send(f"❌ {error}")

        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)

        embed = discord.Embed(
            description=f"🔇 **{member}** has been timed out for `{minutes}m`.\n**Reason:** {reason}",
            color=BRAND_COLOR
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
