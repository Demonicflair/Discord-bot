import discord
from discord.ext import commands
import datetime

from utils.logger import get_logs, save_log, is_log_enabled


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # 🔨 BAN
    # =========================
    @commands.hybrid_command(
        name="ban",
        help="Ban a member from the server.",
        extras={
            "example": "!ban @user Spamming",
            "tips": "Use bans only for serious violations."
        }
    )
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason="No reason"
    ):
        """Ban a member from the server."""

        if member is None:
            return await ctx.send("❌ Usage: !ban @user [reason]")

        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.send("❌ I don't have permission to ban members")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot ban this user")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot ban this user")

        await member.ban(reason=reason)

        embed = discord.Embed(
            title="🔨 User Banned",
            color=discord.Color.red()
        )

        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Reason", value=reason)

        await ctx.send(embed=embed)

        logs = get_logs(ctx.guild.id)

        if logs and is_log_enabled(ctx.guild.id, "ban"):
            channel = ctx.guild.get_channel(logs[0])

            if channel:
                await channel.send(embed=embed)

        save_log(
            ctx.guild.id,
            member.id,
            "ban",
            f"{member} banned by {ctx.author} | Reason: {reason}"
        )

    # =========================
    # 🔓 UNBAN
    # =========================
    @commands.hybrid_command(
        name="unban",
        help="Unban a member using their ID.",
        extras={
            "example": "!unban 123456789",
            "tips": "You need the user's Discord ID."
        }
    )
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        ctx,
        user_id: int = None
    ):
        """Unban a member."""

        if user_id is None:
            return await ctx.send("❌ Usage: !unban <user_id>")

        try:
            user = await self.bot.fetch_user(user_id)

            await ctx.guild.unban(user)

            embed = discord.Embed(
                title="🔓 User Unbanned",
                color=discord.Color.green()
            )

            embed.add_field(name="User", value=f"{user} ({user.id})")
            embed.add_field(name="Moderator", value=ctx.author.mention)

            await ctx.send(embed=embed)

            logs = get_logs(ctx.guild.id)

            if logs and is_log_enabled(ctx.guild.id, "unban"):
                channel = ctx.guild.get_channel(logs[0])

                if channel:
                    await channel.send(embed=embed)

            save_log(
                ctx.guild.id,
                user.id,
                "unban",
                f"{user} unbanned by {ctx.author}"
            )

        except:
            await ctx.send("❌ Failed to unban user.")

    # =========================
    # 👢 KICK
    # =========================
    @commands.hybrid_command(
        name="kick",
        help="Kick a member from the server.",
        extras={
            "example": "!kick @user Breaking rules",
            "tips": "Kick before banning if possible."
        }
    )
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason="No reason"
    ):
        """Kick a member from the server."""

        if member is None:
            return await ctx.send("❌ Usage: !kick @user [reason]")

        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.send("❌ I don't have permission")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot kick this user")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot kick this user")

        await member.kick(reason=reason)

        embed = discord.Embed(
            title="👢 User Kicked",
            color=discord.Color.orange()
        )

        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Reason", value=reason)

        await ctx.send(embed=embed)

        logs = get_logs(ctx.guild.id)

        if logs and is_log_enabled(ctx.guild.id, "kick"):
            channel = ctx.guild.get_channel(logs[0])

            if channel:
                await channel.send(embed=embed)

        save_log(
            ctx.guild.id,
            member.id,
            "kick",
            f"{member} kicked by {ctx.author} | Reason: {reason}"
        )

    # =========================
    # ⚠️ WARN
    # =========================
    @commands.hybrid_command(
        name="warn",
        help="Warn a member.",
        extras={
            "example": "!warn @user Stop spamming",
            "tips": "Warnings help track member behavior."
        }
    )
    @commands.has_permissions(manage_messages=True)
    async def warn(
        self,
        ctx,
        member: discord.Member = None,
        *,
        reason="No reason"
    ):
        """Warn a member."""

        if member is None:
            return await ctx.send("❌ Usage: !warn @user [reason]")

        embed = discord.Embed(
            title="⚠️ User Warned",
            color=discord.Color.yellow()
        )

        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Reason", value=reason)

        await ctx.send(embed=embed)

        logs = get_logs(ctx.guild.id)

        if logs and is_log_enabled(ctx.guild.id, "warn"):
            channel = ctx.guild.get_channel(logs[0])

            if channel:
                await channel.send(embed=embed)

        save_log(
            ctx.guild.id,
            member.id,
            "warn",
            f"{member} warned by {ctx.author} | Reason: {reason}"
        )

    # =========================
    # 🔇 MUTE / TIMEOUT
    # =========================
    @commands.hybrid_command(
        name="mute",
        help="Timeout a member for a specific duration.",
        extras={
            "example": "!mute @user 10 Spamming",
            "tips": "Duration is in minutes."
        }
    )
    @commands.has_permissions(moderate_members=True)
    async def mute(
        self,
        ctx,
        member: discord.Member = None,
        duration: int = 5,
        *,
        reason="No reason"
    ):
        """Timeout a member."""

        if member is None:
            return await ctx.send("❌ Usage: !mute @user <minutes> [reason]")

        if not ctx.guild.me.guild_permissions.moderate_members:
            return await ctx.send("❌ I don't have permission to timeout members")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot mute this user")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot mute this user")

        if duration <= 0:
            return await ctx.send("❌ Duration must be greater than 0")

        until = discord.utils.utcnow() + datetime.timedelta(minutes=duration)

        await member.timeout(
            until,
            reason=reason
        )

        embed = discord.Embed(
            title="🔇 User Muted",
            color=discord.Color.blurple()
        )

        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Duration", value=f"{duration} minute(s)")
        embed.add_field(name="Reason", value=reason)

        await ctx.send(embed=embed)

        logs = get_logs(ctx.guild.id)

        if logs and is_log_enabled(ctx.guild.id, "mute"):
            channel = ctx.guild.get_channel(logs[0])

            if channel:
                await channel.send(embed=embed)

        save_log(
            ctx.guild.id,
            member.id,
            "mute",
            f"{member} muted by {ctx.author} for {duration}m | Reason: {reason}"
        )

    # =========================
    # 🔊 UNMUTE / UNTIMEOUT
    # =========================
    @commands.hybrid_command(
        name="unmute",
        help="Remove timeout from a member.",
        extras={
            "example": "!unmute @user",
            "tips": "Removes active timeout instantly."
        }
    )
    @commands.has_permissions(moderate_members=True)
    async def unmute(
        self,
        ctx,
        member: discord.Member = None
    ):
        """Remove timeout from a member."""

        if member is None:
            return await ctx.send("❌ Usage: !unmute @user")

        try:
            await member.timeout(None)

            embed = discord.Embed(
                title="🔊 User Unmuted",
                color=discord.Color.green()
            )

            embed.add_field(name="User", value=member.mention)
            embed.add_field(name="Moderator", value=ctx.author.mention)

            await ctx.send(embed=embed)

            logs = get_logs(ctx.guild.id)

            if logs and is_log_enabled(ctx.guild.id, "unmute"):
                channel = ctx.guild.get_channel(logs[0])

                if channel:
                    await channel.send(embed=embed)

            save_log(
                ctx.guild.id,
                member.id,
                "unmute",
                f"{member} unmuted by {ctx.author}"
            )

        except:
            await ctx.send("❌ Failed to unmute member.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
