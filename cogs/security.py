import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import datetime
import re
from utils.dispatch import dispatch_log

DB_PATH = "data.db"
# Patterns for common scams
SCAM_PATTERN = r"(free.*nitro|nitro.*free|steam.*gift|claim.*reward|discord.*gift)"

class SecurityAI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.heat_levels = {} # Temporary in-memory scoring {(guild_id, user_id): score}

    async def get_security_setting(self, guild_id, feature):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT enabled FROM settings WHERE guild_id=? AND feature=?", (guild_id, feature)) as cur:
                r = await cur.fetchone()
                return r is None or r[0] == 1 # Defaults to ON

    async def update_heat(self, message, points, reason):
        """Adds 'heat' to a user. If they get too hot, they get punished."""
        if message.author.guild_permissions.manage_messages: return
        
        gid, uid = message.guild.id, message.author.id
        current_heat = self.heat_levels.get((gid, uid), 0) + points
        self.heat_levels[(gid, uid)] = current_heat

        # PUNISHMENT LADDER
        if current_heat >= 10:
            await message.author.ban(reason=f"🚨 Security AI: Critical Heat ({reason})")
            await dispatch_log(message.guild, "security", f"⛔ **Banned:** {message.author}\n**Reason:** Reached Critical Heat (10+ pts)\n**Last Trigger:** {reason}")
            self.heat_levels[(gid, uid)] = 0 # Reset after ban
            
        elif current_heat >= 6:
            # 1 hour timeout
            await message.author.timeout(discord.utils.utcnow() + datetime.timedelta(hours=1), reason=reason)
            await message.channel.send(f"🔇 {message.author.mention} has been silenced for 1 hour. (AI Flag: {reason})", delete_after=10)
            
        elif current_heat >= 3:
            await message.channel.send(f"⚠️ {message.author.mention}, watch your behavior. [AI Warning: {reason}]", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        
        gid = message.guild.id
        content = message.content.lower()

        # 1. SCAM / PHISHING PROTECTION
        if await self.get_security_setting(gid, "scam_protection"):
            if re.search(SCAM_PATTERN, content):
                try: await message.delete()
                except: pass
                await self.update_heat(message, 5, "Scam/Phishing Link")
                return # Stop further checks for this message

        # 2. MASS MENTION PROTECTION
        if await self.get_security_setting(gid, "mention_protection"):
            if len(message.mentions) > 5:
                try: await message.delete()
                except: pass
                await self.update_heat(message, 4, "Mass Mention")

    # =========================
    # ⚙️ COMMANDS
    # =========================
    @commands.hybrid_group(name="security", description="⚙️ Manage AI Security settings.")
    @commands.has_permissions(administrator=True)
    async def security(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `!security status` to see current heat levels.")

    @security.command(name="reset", description="🔥 Reset the AI heat for a specific user.")
    async def reset_heat(self, ctx, user: discord.Member):
        self.heat_levels[(ctx.guild.id, user.id)] = 0
        await ctx.send(f"✅ AI Heat for {user.mention} has been cleared.")

    @security.command(name="status", description="📈 View a user's current AI heat level.")
    async def heat_status(self, ctx, user: discord.Member):
        score = self.heat_levels.get((ctx.guild.id, user.id), 0)
        status = "🟢 Safe" if score < 3 else "🟡 Warning" if score < 6 else "🔴 Dangerous"
        
        embed = discord.Embed(title="🛡️ AI Security Profile", color=0x2b2d31)
        embed.add_field(name="User", value=user.mention)
        embed.add_field(name="Heat Level", value=f"`{score}/10`")
        embed.add_field(name="Risk Status", value=status)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SecurityAI(bot))
