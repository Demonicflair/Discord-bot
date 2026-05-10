import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import time
from utils.dispatch import dispatch_log

DB_PATH = "data.db"

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # In-memory tracking for fast rate-limiting
        self.cooldowns = {} 

    async def is_whitelisted(self, guild_id, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM settings WHERE guild_id=? AND feature='whitelist' AND enabled=?", (guild_id, user_id)) as cur:
                return await cur.fetchone() is not None

    async def punish(self, guild, member, action_type):
        """The 'Hammer' logic for unauthorized actions."""
        if member.id == guild.owner_id: return
        
        try:
            await member.ban(reason=f"🛑 Dem Anti-Nuke: Unauthorized {action_type}")
            await dispatch_log(guild, "antinuke", f"🚨 **Banned:** {member.mention}\n**Reason:** Mass {action_type} detected.")
        except:
            # Fallback if bot can't ban (e.g. role hierarchy)
            try: await member.edit(roles=[], reason="Anti-Nuke: Stripping permissions")
            except: pass

    # =========================
    # 💥 CHANNEL PROTECTION (Auto-Recovery)
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        # Fetch audit logs to see who did it
        async for entry in guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
            user = entry.user
            if user.id == self.bot.user.id or await self.is_whitelisted(guild.id, user.id):
                return

            # RECOVERY: Re-create the channel
            new_channel = await channel.clone(reason="Anti-Nuke: Channel Recovery")
            await new_channel.edit(position=channel.position)
            
            # PUNISH: Ban the user
            await self.punish(guild, user, "Channel Deletion")
            await new_channel.send(f"🛡️ **Anti-Nuke System:** I have recovered this channel after it was deleted by {user.mention}.")

    # =========================
    # 🎭 ROLE PROTECTION
    # =========================
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        async for entry in guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
            user = entry.user
            if user.id == self.bot.user.id or await self.is_whitelisted(guild.id, user.id):
                return

            await self.punish(guild, user, "Role Deletion")

    # =========================
    # 🤖 BOT ADDITION PROTECTION
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.bot: return
        
        guild = member.guild
        async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
            user = entry.user
            if await self.is_whitelisted(guild.id, user.id):
                return

            # Ban the bot AND the person who invited it
            await member.ban(reason="Anti-Nuke: Unauthorized Bot")
            await self.punish(guild, user, "Unauthorized Bot Invite")

    # =========================
    # ⚙️ CONFIG COMMANDS (Hybrid)
    # =========================
    @commands.hybrid_group(name="antinuke", description="🛡️ Configure the Anti-Nuke Shield.")
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Usage: `!antinuke <enable/disable/whitelist>`")

    @antinuke.command(name="whitelist", description="⚪ Whitelist a user from Anti-Nuke.")
    async def whitelist(self, ctx, user: discord.User):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO settings VALUES (?, 'whitelist', ?)", (ctx.guild.id, user.id))
            await db.commit()
        await ctx.send(f"✅ {user.mention} is now whitelisted from Anti-Nuke.")

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
