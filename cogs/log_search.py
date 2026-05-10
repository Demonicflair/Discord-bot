import discord
from discord.ext import commands
from discord import app_commands
from utils.logger import set_log_state # Matching our upgraded logger name

# Pre-defined suggestions for Autocomplete
LOG_SUGGESTIONS = [
    "ban", "unban", "kick", "warn", "mute", "unmute",
    "ticket", "security", "antinuke", "raid", "spam", "lockdown"
]

class LogControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # ✅ AUTOCOMPLETE LOGIC
    # =========================
    async def log_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=l.title(), value=l)
            for l in LOG_SUGGESTIONS if current.lower() in l.lower()
        ][:25]

    # =========================
    # ✅ ENABLE LOGS
    # =========================
    @commands.hybrid_command(
        name="log_enable",
        help="Enable a specific log type.",
        extras={
            "example": "!log_enable ban",
            "tips": "Enable moderation, ticket, antinuke, or security logs."
        }
    )
    @app_commands.describe(log="The log type you want to enable")
    @app_commands.autocomplete(log=log_autocomplete)
    @commands.has_permissions(manage_guild=True)
    async def log_enable(self, ctx, log: str = None):
        """Enable a specific log type."""
        if log is None:
            return await ctx.send("❌ Usage: `!log_enable <log_type>`", delete_after=10)

        log = log.lower()
        await set_log_state(ctx.guild.id, log, True)

        embed = discord.Embed(
            title="✅ Logs Enabled",
            description=f"Successfully activated **{log}** logs for this server.",
            color=discord.Color.green()
        )
        embed.add_field(name="📘 Example", value=f"`!log_enable {log}`", inline=False)
        embed.set_footer(text=f"Action by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

    # =========================
    # ❌ DISABLE LOGS
    # =========================
    @commands.hybrid_command(
        name="log_disable",
        help="Disable a specific log type.",
        extras={
            "example": "!log_disable ticket",
            "tips": "Disable logs that are too spammy or unnecessary."
        }
    )
    @app_commands.describe(log="The log type you want to disable")
    @app_commands.autocomplete(log=log_autocomplete)
    @commands.has_permissions(manage_guild=True)
    async def log_disable(self, ctx, log: str = None):
        """Disable a specific log type."""
        if log is None:
            return await ctx.send("❌ Usage: `!log_disable <log_type>`", delete_after=10)

        log = log.lower()
        await set_log_state(ctx.guild.id, log, False)

        embed = discord.Embed(
            title="❌ Logs Disabled",
            description=f"Successfully deactivated **{log}** logs.",
            color=discord.Color.red()
        )
        embed.add_field(name="📘 Example", value=f"`!log_disable {log}`", inline=False)
        embed.set_footer(text=f"Action by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LogControl(bot))
    
