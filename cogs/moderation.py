from discord.ext import commands
import discord

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔨 BAN COMMAND
    @commands.command(name="ban")
    async def ban(self, ctx, member: discord.Member = None, *, reason=None):

        # ❌ Missing argument
        if member is None:
            return await ctx.send("❌ Usage: !ban @user [reason]")

        # ❌ User permission check
        if not ctx.author.guild_permissions.ban_members:
            return await ctx.send("❌ You don't have permission to ban members")

        # ❌ Bot permission check
        if not ctx.guild.me.guild_permissions.ban_members:
            return await ctx.send("❌ I don't have permission to ban members")

        # ❌ Role hierarchy (user)
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot ban this user (higher or equal role)")

        # ❌ Role hierarchy (bot)
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot ban this user (my role is lower)")

        # ✅ Execute ban
        try:
            await member.ban(reason=reason)
            await ctx.send(
                f"🔨 {member} has been banned\nReason: {reason or 'No reason'}"
            )
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban this user")

    # 👢 KICK COMMAND
    @commands.command(name="kick")
    async def kick(self, ctx, member: discord.Member = None, *, reason=None):

        if member is None:
            return await ctx.send("❌ Usage: !kick @user [reason]")

        if not ctx.author.guild_permissions.kick_members:
            return await ctx.send("❌ You don't have permission to kick members")

        if not ctx.guild.me.guild_permissions.kick_members:
            return await ctx.send("❌ I don't have permission to kick members")

        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("❌ You cannot kick this user")

        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send("❌ I cannot kick this user")

        try:
            await member.kick(reason=reason)
            await ctx.send(
                f"👢 {member} has been kicked\nReason: {reason or 'No reason'}"
            )
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick this user")

    # ⚠️ WARN COMMAND (basic)
    @commands.command(name="warn")
    async def warn(self, ctx, member: discord.Member = None, *, reason=None):

        if member is None:
            return await ctx.send("❌ Usage: !warn @user [reason]")

        await ctx.send(
            f"⚠️ {member.mention} has been warned\nReason: {reason or 'No reason'}"
        )

    # ❗ GLOBAL ERROR HANDLER
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ User not found")

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command")

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I am missing required permissions")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing arguments. Check command usage")

        else:
            print(error)  # keep for debugging


async def setup(bot):
    await bot.add_cog(Moderation(bot))
