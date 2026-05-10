import discord
from discord.ext import commands
import datetime
import aiosqlite

from utils.logger import get_logs, save_log, is_log_enabled

DB_PATH = "bot.db"

# =========================
# EMBED HELPER
# =========================
def build_embed(title, description=None, color=discord.Color.blurple()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )
    return embed

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Helper to check if Logging is enabled globally for the server
    async def is_logging_active(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT enabled FROM settings WHERE guild_id=? AND feature=?", (guild_id, "logging")) as cur:
                r = await cur.fetchone()
                return r is None or r[0] == 1

    async def send_log_safe(self, guild, log_type, embed):
        if not await self.is_logging_active(guild.id): return
        
        logs = get_logs(guild.id)
        if logs and is_log_enabled(guild.id, log_type):
            channel = guild.get_channel(logs[1])
            if channel:
                try: await channel.send(embed=embed)
                except: pass
        save_log(guild.id, 0, log_type, embed.title)

    # =========================
    # MEMBER EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = build_embed("✅ Member Joined", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 User", value=f"{member.mention}\n`{member.id}`", inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.set_footer(text=f"Total Members: {member.guild.member_count}")
        await self.send_log_safe(member.guild, "member_join", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Elite Logic: Check Audit Logs to see if they were Kicked/Banned or just left
        action = "Left"
        reason = "Self-departure"
        color = discord.Color.red()

        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                action = f"Kicked by {entry.user}"
                reason = entry.reason or "No reason provided"
                break

        embed = build_embed(f"❌ Member {action}", f"Reason: {reason}", color=color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 User", value=f"**{member}**\n`{member.id}`")
        await self.send_log_safe(member.guild, "member_leave", embed)

    # =========================
    # MESSAGE EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild: return

        # 1. Standard Deletion Log
        embed = build_embed("🗑️ Message Deleted", color=discord.Color.red())
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=message.content[:1024] or "[No Text/Embed Only]", inline=False)
        
        # 2. Elite: Ghost Ping Detection (Integrated)
        if message.mentions:
            embed.title = "👻 Ghost Ping Detected"
            embed.add_field(name="🔔 Pings", value=", ".join([m.mention for m in message.mentions]))
            await self.send_log_safe(message.guild, "ghost_ping", embed)
        else:
            await self.send_log_safe(message.guild, "message_delete", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content: return

        embed = build_embed("✏️ Message Edited", color=discord.Color.orange())
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Before", value=before.content[:512] or "None", inline=False)
        embed.add_field(name="After", value=after.content[:512] or "None", inline=False)
        await self.send_log_safe(before.guild, "message_edit", embed)

    # =========================
    # VOICE & CHANNEL EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel: return

        if not before.channel:
            msg, color = f"📥 {member.mention} joined **{after.channel.name}**", discord.Color.green()
        elif not after.channel:
            msg, color = f"📤 {member.mention} left **{before.channel.name}**", discord.Color.red()
        else:
            msg, color = f"🔄 {member.mention} moved: **{before.channel.name}** ➔ **{after.channel.name}**", discord.Color.blue()

        embed = build_embed("🎤 Voice Update", msg, color)
        await self.send_log_safe(member.guild, "voice", embed)

async def setup(bot):
    await bot.add_cog(Events(bot))
