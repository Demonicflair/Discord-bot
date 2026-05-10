import discord
from discord.ext import commands
from discord import app_commands

from utils.logger import (
    set_log_state,  # Renamed to match the upgraded logger
    set_log_channel,
    get_logs
)

# =========================
# CONFIG
# =========================
VALID_LOGS = [
    "ban", "unban", "kick", "warn", "mute", "unmute",
    "ticket", "security", "antinuke", "raid", "spam", "lockdown"
]

LOG_CHOICES = [
    app_commands.Choice(name=log.title(), value=log)
    for log in VALID_LOGS
]

DEM_COLOR = 0x2b2d31

# =========================
# EMBEDS
# =========================
def log_embed(text, success=True):
    return discord.Embed(
        description=f"{'✅' if success else '❌'} {text}",
        color=discord.Color.green() if success else discord.Color.red()
    )

# =========================
# LOG CONTROL COG
# =========================
class LogControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # TOGGLE LOGS
    # =========================
    @commands.hybrid_command(name="log_enable", description="Enable a specific log type.")
    @app_commands.choices(log=LOG_CHOICES)
    @commands.has_permissions(manage_guild=True)
    async def log_enable(self, ctx, log: app_commands.Choice[str]):
        await set_log_state(ctx.guild.id, log.value, True)
        await ctx.send(embed=log_embed(f"Enabled `{log.value}` logs."), ephemeral=True)

    @commands.hybrid_command(name="log_disable", description="Disable a specific log type.")
    @app_commands.choices(log=LOG_CHOICES)
    @commands.has_permissions(manage_guild=True)
    async def log_disable(self, ctx, log: app_commands.Choice[str]):
        await set_log_state(ctx.guild.id, log.value, False)
        await ctx.send(embed=log_embed(f"Disabled `{log.value}` logs."), ephemeral=True)

    # =========================
    # CHANNEL SETUP
    # =========================
    @commands.hybrid_command(name="set_modlog", description="Set the moderation log channel.")
    @commands.has_permissions(manage_guild=True)
    async def set_modlog(self, ctx, channel: discord.TextChannel):
        # Permission check
        if not channel.permissions_for(ctx.guild.me).send_messages:
            return await ctx.send(embed=log_embed("I don't have permission to send messages in that channel!", False))

        logs = await get_logs(ctx.guild.id)
        bot_log = logs[1] if logs else None

        await set_log_channel(ctx.guild.id, mod_log=channel.id, bot_log=bot_log)
        await ctx.send(embed=log_embed(f"Moderation logs set to {channel.mention}"))

    @commands.hybrid_command(name="set_botlog", description="Set the bot/system log channel.")
    @commands.has_permissions(manage_guild=True)
    async def set_botlog(self, ctx, channel: discord.TextChannel):
        if not channel.permissions_for(ctx.guild.me).send_messages:
            return await ctx.send(embed=log_embed("I don't have permission to send messages in that channel!", False))

        logs = await get_logs(ctx.guild.id)
        mod_log = logs[0] if logs else None

        await set_log_channel(ctx.guild.id, mod_log=mod_log, bot_log=channel.id)
        await ctx.send(embed=log_embed(f"Bot logs set to {channel.mention}"))

    # =========================
    # STATUS VIEW
    # =========================
    @commands.hybrid_command(name="log_settings", description="View current logging setup.")
    @commands.has_permissions(manage_guild=True)
    async def log_settings(self, ctx):
        logs = await get_logs(ctx.guild.id)
        
        mod_log = f"<#{logs[0]}>" if logs and logs[0] else "`Not Set`"
        bot_log = f"<#{logs[1]}>" if logs and logs[1] else "`Not Set`"

        embed = discord.Embed(title="📁 Dem Logging Configuration", color=DEM_COLOR)
        embed.add_field(name="🛠️ Moderation Channel", value=mod_log, inline=True)
        embed.add_field(name="🤖 Bot/System Channel", value=bot_log, inline=True)
        
        # Show all valid logs in a clean list
        embed.add_field(name="📌 Log Types", value="`" + "`, `".join(VALID_LOGS) + "`", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LogControl(bot))
    
