# events.py

import discord
from discord.ext import commands
import io

from utils.logger import get_logs, save_log, is_log_enabled

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


# =========================
# SEND LOG
# =========================
async def send_log(guild, log_type, embed=None, file=None):

    logs = get_logs(guild.id)

    if not logs:
        return

    channel = guild.get_channel(logs[1])

    if not channel:
        return

    if not is_log_enabled(guild.id, log_type):
        return

    try:

        if file:
            await channel.send(embed=embed, file=file)

        else:
            await channel.send(embed=embed)

    except:
        pass


# =========================
# EVENTS COG
# =========================
class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # MEMBER JOIN
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):

        embed = build_embed(
            "✅ Member Joined",
            color=discord.Color.green()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="👤 User",
            value=f"{member.mention}\n`{member.id}`",
            inline=False
        )

        embed.add_field(
            name="📅 Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=False
        )

        embed.add_field(
            name="📈 Member Count",
            value=str(member.guild.member_count),
            inline=False
        )

        await send_log(member.guild, "member_join", embed)

        save_log(
            member.guild.id,
            member.id,
            "member_join",
            f"{member} joined"
        )

    # =========================
    # MEMBER LEAVE
    # =========================
    @commands.Cog.listener()
    async def on_member_remove(self, member):

        embed = build_embed(
            "❌ Member Left",
            color=discord.Color.red()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="👤 User",
            value=f"{member}\n`{member.id}`",
            inline=False
        )

        embed.add_field(
            name="📉 Member Count",
            value=str(member.guild.member_count),
            inline=False
        )

        await send_log(member.guild, "member_leave", embed)

        save_log(
            member.guild.id,
            member.id,
            "member_leave",
            f"{member} left"
        )

    # =========================
    # BOOST LOGS
    # =========================
    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        # BOOST START
        if not before.premium_since and after.premium_since:

            embed = build_embed(
                "🚀 Server Boosted",
                f"{after.mention} boosted the server!",
                discord.Color.purple()
            )

            embed.set_thumbnail(url=after.display_avatar.url)

            await send_log(after.guild, "boost", embed)

            save_log(
                after.guild.id,
                after.id,
                "boost",
                f"{after} boosted the server"
            )

        # NICKNAME CHANGE
        if before.nick != after.nick:

            embed = build_embed(
                "📝 Nickname Updated",
                color=discord.Color.orange()
            )

            embed.add_field(
                name="👤 User",
                value=after.mention,
                inline=False
            )

            embed.add_field(
                name="Before",
                value=before.nick or before.name,
                inline=True
            )

            embed.add_field(
                name="After",
                value=after.nick or after.name,
                inline=True
            )

            await send_log(after.guild, "nickname", embed)

            save_log(
                after.guild.id,
                after.id,
                "nickname",
                f"{before} nickname changed"
            )

        # ROLE UPDATE
        if before.roles != after.roles:

            before_roles = set(before.roles)
            after_roles = set(after.roles)

            gained = after_roles - before_roles
            lost = before_roles - after_roles

            text = ""

            if gained:
                text += f"➕ Added: {', '.join(r.mention for r in gained)}\n"

            if lost:
                text += f"➖ Removed: {', '.join(r.mention for r in lost)}"

            embed = build_embed(
                "🎭 Roles Updated",
                text,
                discord.Color.blurple()
            )

            embed.add_field(
                name="👤 User",
                value=after.mention,
                inline=False
            )

            await send_log(after.guild, "roles", embed)

            save_log(
                after.guild.id,
                after.id,
                "roles",
                f"{after} roles updated"
            )

    # =========================
    # MESSAGE DELETE
    # =========================
    @commands.Cog.listener()
    async def on_message_delete(self, message):

        if message.author.bot or not message.guild:
            return

        embed = build_embed(
            "🗑️ Message Deleted",
            color=discord.Color.red()
        )

        embed.add_field(
            name="👤 Author",
            value=message.author.mention,
            inline=False
        )

        embed.add_field(
            name="📍 Channel",
            value=message.channel.mention,
            inline=False
        )

        embed.add_field(
            name="💬 Content",
            value=message.content[:1000] or "No content",
            inline=False
        )

        # ATTACHMENT LOGS
        if message.attachments:

            files = "\n".join(a.url for a in message.attachments)

            embed.add_field(
                name="📎 Attachments",
                value=files[:1000],
                inline=False
            )

        # STICKER LOGS
        if message.stickers:

            stickers = ", ".join(s.name for s in message.stickers)

            embed.add_field(
                name="🎟️ Stickers",
                value=stickers,
                inline=False
            )

        await send_log(message.guild, "message_delete", embed)

        save_log(
            message.guild.id,
            message.author.id,
            "message_delete",
            f"{message.author} deleted message"
        )

    # =========================
    # MESSAGE EDIT
    # =========================
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):

        if before.author.bot:
            return

        if before.content == after.content:
            return

        embed = build_embed(
            "✏️ Message Edited",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Author",
            value=before.author.mention,
            inline=False
        )

        embed.add_field(
            name="📍 Channel",
            value=before.channel.mention,
            inline=False
        )

        embed.add_field(
            name="Before",
            value=before.content[:1000] or "None",
            inline=False
        )

        embed.add_field(
            name="After",
            value=after.content[:1000] or "None",
            inline=False
        )

        await send_log(before.guild, "message_edit", embed)

        save_log(
            before.guild.id,
            before.author.id,
            "message_edit",
            f"{before.author} edited message"
        )

    # =========================
    # CHANNEL CREATE
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):

        embed = build_embed(
            "📁 Channel Created",
            f"{channel.mention}",
            discord.Color.green()
        )

        await send_log(channel.guild, "channel_create", embed)

        save_log(
            channel.guild.id,
            0,
            "channel_create",
            f"{channel.name} created"
        )

    # =========================
    # CHANNEL DELETE
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        embed = build_embed(
            "🗑️ Channel Deleted",
            f"`{channel.name}`",
            discord.Color.red()
        )

        await send_log(channel.guild, "channel_delete", embed)

        save_log(
            channel.guild.id,
            0,
            "channel_delete",
            f"{channel.name} deleted"
        )

    # =========================
    # VOICE LOGS
    # =========================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        if before.channel == after.channel:
            return

        # JOIN
        if before.channel is None and after.channel:

            embed = build_embed(
                "🎤 Voice Join",
                f"{member.mention} joined {after.channel.mention}",
                discord.Color.green()
            )

            await send_log(member.guild, "voice", embed)

        # LEAVE
        elif before.channel and after.channel is None:

            embed = build_embed(
                "📤 Voice Leave",
                f"{member.mention} left {before.channel.mention}",
                discord.Color.red()
            )

            await send_log(member.guild, "voice", embed)

        # MOVE
        elif before.channel != after.channel:

            embed = build_embed(
                "🔄 Voice Move",
                (
                    f"{member.mention}\n"
                    f"From: {before.channel.mention}\n"
                    f"To: {after.channel.mention}"
                ),
                discord.Color.orange()
            )

            await send_log(member.guild, "voice", embed)

    # =========================
    # EMOJI LOGS
    # =========================
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):

        before_set = set(e.name for e in before)
        after_set = set(e.name for e in after)

        added = after_set - before_set
        removed = before_set - after_set

        if added:

            embed = build_embed(
                "😀 Emoji Added",
                ", ".join(added),
                discord.Color.green()
            )

            await send_log(guild, "emoji", embed)

        if removed:

            embed = build_embed(
                "❌ Emoji Removed",
                ", ".join(removed),
                discord.Color.red()
            )

            await send_log(guild, "emoji", embed)

    # =========================
    # ANTI GHOST PING
    # =========================
    @commands.Cog.listener()
    async def on_message_delete(self, message):

        if not message.guild:
            return

        if message.author.bot:
            return

        if not message.mentions:
            return

        mentioned = ", ".join(m.mention for m in message.mentions)

        embed = build_embed(
            "👻 Ghost Ping Detected",
            (
                f"👤 Author: {message.author.mention}\n"
                f"📍 Channel: {message.channel.mention}\n"
                f"🔔 Mentioned: {mentioned}"
            ),
            discord.Color.red()
        )

        await send_log(message.guild, "ghost_ping", embed)


# =========================
# SETUP
# =========================
async def setup(bot):

    await bot.add_cog(Events(bot))
