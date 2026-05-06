import discord
from discord.ext import commands
from discord import app_commands

from utils.logger import get_logs, save_log, is_log_enabled


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # 🔨 BAN (PREFIX)
    # =========================
    @commands.command(name="ban")
    async def ban_prefix(self, ctx, member: discord.Member = None, *, reason=None):

        if member is None:
            return await ctx.send("❌ Usage: !ban @user [reason]")

        if not ctx.author.guild_permissions.ban_members:
            return await ctx.send("❌ You don't have permission to ban members")

        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.send("❌ I don't have permission to ban members")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot ban this user (higher role)")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot ban this user (my role is lower)")

        await member.ban(reason=reason)

        embed = discord.Embed(title="🔨 User Banned", color=discord.Color.red())
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Reason", value=reason or "No reason")

        await ctx.send(embed=embed)

        # ===== LOG SYSTEM =====
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
    # 🔨 BAN (SLASH)
    # =========================
    @app_commands.command(name="ban", description="Ban a user")
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):

        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ You don't have permission", ephemeral=True)

        if not interaction.guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ I don't have permission", ephemeral=True)

        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ You cannot ban this user", ephemeral=True)

        if member.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ I cannot ban this user", ephemeral=True)

        await member.ban(reason=reason)

        embed = discord.Embed(title="🔨 User Banned", color=discord.Color.red())
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=interaction.user.mention)
        embed.add_field(name="Reason", value=reason)

        await interaction.response.send_message(embed=embed)

        # ===== LOG SYSTEM =====
        logs = get_logs(interaction.guild.id)

        if logs and is_log_enabled(interaction.guild.id, "ban"):
            channel = interaction.guild.get_channel(logs[0])
            if channel:
                await channel.send(embed=embed)

        save_log(
            interaction.guild.id,
            member.id,
            "ban",
            f"{member} banned by {interaction.user} | Reason: {reason}"
        )

    # =========================
    # 👢 KICK (PREFIX)
    # =========================
    @commands.command(name="kick")
    async def kick_prefix(self, ctx, member: discord.Member = None, *, reason=None):

        if member is None:
            return await ctx.send("❌ Usage: !kick @user [reason]")

        if not ctx.author.guild_permissions.kick_members:
            return await ctx.send("❌ You don't have permission")

        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.send("❌ I don't have permission")

        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ You cannot kick this user")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot kick this user")

        await member.kick(reason=reason)

        embed = discord.Embed(title="👢 User Kicked", color=discord.Color.orange())
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=ctx.author.mention)
        embed.add_field(name="Reason", value=reason or "No reason")

        await ctx.send(embed=embed)

        # ===== LOG SYSTEM =====
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
    # 👢 KICK (SLASH)
    # =========================
    @app_commands.command(name="kick", description="Kick a user")
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):

        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ No permission", ephemeral=True)

        if not interaction.guild.me.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ I don't have permission", ephemeral=True)

        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ Cannot kick this user", ephemeral=True)

        if member.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("❌ I cannot kick this user", ephemeral=True)

        await member.kick(reason=reason)

        embed = discord.Embed(title="👢 User Kicked", color=discord.Color.orange())
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Moderator", value=interaction.user.mention)
        embed.add_field(name="Reason", value=reason)

        await interaction.response.send_message(embed=embed)

        # ===== LOG SYSTEM =====
        logs = get_logs(interaction.guild.id)

        if logs and is_log_enabled(interaction.guild.id, "kick"):
            channel = interaction.guild.get_channel(logs[0])
            if channel:
                await channel.send(embed=embed)

        save_log(
            interaction.guild.id,
            member.id,
            "kick",
            f"{member} kicked by {interaction.user} | Reason: {reason}"
        )

    # =========================
    # ⚠️ WARN (BOTH)
    # =========================
    @commands.command(name="warn")
    async def warn_prefix(self, ctx, member: discord.Member = None, *, reason=None):

        if member is None:
            return await ctx.send("❌ Usage: !warn @user [reason]")

        msg = f"⚠️ {member.mention} warned\nReason: {reason or 'No reason'}"
        await ctx.send(msg)

        save_log(
            ctx.guild.id,
            member.id,
            "warn",
            f"{member} warned by {ctx.author} | Reason: {reason}"
        )

    @app_commands.command(name="warn", description="Warn a user")
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):

        msg = f"⚠️ {member.mention} warned\nReason: {reason}"
        await interaction.response.send_message(msg)

        save_log(
            interaction.guild.id,
            member.id,
            "warn",
            f"{member} warned by {interaction.user} | Reason: {reason}"
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
