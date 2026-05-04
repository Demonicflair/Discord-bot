
import discord
from discord.ext import commands
from discord import app_commands

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
        embed.add_field(name="Reason", value=reason or "No reason")

        await ctx.send(embed=embed)

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
        embed.add_field(name="Reason", value=reason)

        await interaction.response.send_message(embed=embed)

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

        await ctx.send(f"👢 {member} kicked")

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
        await interaction.response.send_message(f"👢 Kicked {member}")

    # =========================
    # ⚠️ WARN (BOTH)
    # =========================
    @commands.command(name="warn")
    async def warn_prefix(self, ctx, member: discord.Member = None, *, reason=None):

        if member is None:
            return await ctx.send("❌ Usage: !warn @user [reason]")

        await ctx.send(f"⚠️ {member.mention} warned\nReason: {reason or 'No reason'}")

    @app_commands.command(name="warn", description="Warn a user")
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):

        await interaction.response.send_message(
            f"⚠️ {member.mention} warned\nReason: {reason}"
        )

async def setup(bot):
    await bot.add_cog(Moderation(bot))
