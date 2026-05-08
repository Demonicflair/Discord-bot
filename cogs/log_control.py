import discord

from discord.ext import commands
from discord import app_commands

from utils.logger import (
    set_log,
    set_log_channel,
    get_logs
)

# =========================
# VALID LOG TYPES
# =========================
VALID_LOGS = [

    "ban",
    "unban",

    "kick",

    "warn",

    "mute",
    "unmute",

    "ticket",

    "security",

    "antinuke",

    "raid",

    "spam",

    "lockdown"
]

# =========================
# CHOICES
# =========================
LOG_CHOICES = [

    app_commands.Choice(
        name=log.title(),
        value=log
    )

    for log in VALID_LOGS
]

# =========================
# EMBED
# =========================
def success_embed(text):

    return discord.Embed(
        description=f"✅ {text}",
        color=discord.Color.green()
    )

def error_embed(text):

    return discord.Embed(
        description=f"❌ {text}",
        color=discord.Color.red()
    )

# =========================
# LOG CONTROL
# =========================
class LogControl(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # LOG ENABLE
    # =========================
    @commands.hybrid_command(
        name="log_enable",
        help="Enable a specific log type.",
        extras={
            "example": "!log_enable ban",
            "tips": "Enable only logs you actually need."
        }
    )
    @app_commands.choices(log=LOG_CHOICES)
    @commands.has_permissions(manage_guild=True)
    async def log_enable(
        self,
        ctx,
        log: app_commands.Choice[str]
    ):
        """Enable a log type."""

        set_log(
            ctx.guild.id,
            log.value,
            True
        )

        await ctx.send(
            embed=success_embed(
                f"Enabled `{log.value}` logs"
            )
        )

    # =========================
    # LOG DISABLE
    # =========================
    @commands.hybrid_command(
        name="log_disable",
        help="Disable a specific log type.",
        extras={
            "example": "!log_disable spam",
            "tips": "Disable unnecessary logs to reduce spam."
        }
    )
    @app_commands.choices(log=LOG_CHOICES)
    @commands.has_permissions(manage_guild=True)
    async def log_disable(
        self,
        ctx,
        log: app_commands.Choice[str]
    ):
        """Disable a log type."""

        set_log(
            ctx.guild.id,
            log.value,
            False
        )

        await ctx.send(
            embed=success_embed(
                f"Disabled `{log.value}` logs"
            )
        )

    # =========================
    # SET MOD LOG
    # =========================
    @commands.hybrid_command(
        name="set_modlog",
        help="Set the moderation log channel.",
        extras={
            "example": "!set_modlog #mod-logs",
            "tips": "Moderation actions will be sent here."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def set_modlog(
        self,
        ctx,
        channel: discord.TextChannel = None
    ):
        """Set the moderation log channel."""

        if channel is None:

            return await ctx.send(
                embed=error_embed(
                    "Usage: !set_modlog #channel"
                )
            )

        logs = get_logs(ctx.guild.id)

        bot_log = logs[1] if logs else None

        set_log_channel(
            ctx.guild.id,
            mod_log=channel.id,
            bot_log=bot_log
        )

        await ctx.send(
            embed=success_embed(
                f"Moderation logs set to {channel.mention}"
            )
        )

    # =========================
    # SET BOT LOG
    # =========================
    @commands.hybrid_command(
        name="set_botlog",
        help="Set the bot/system log channel.",
        extras={
            "example": "!set_botlog #bot-logs",
            "tips": "Security and ticket logs will appear here."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def set_botlog(
        self,
        ctx,
        channel: discord.TextChannel = None
    ):
        """Set the bot log channel."""

        if channel is None:

            return await ctx.send(
                embed=error_embed(
                    "Usage: !set_botlog #channel"
                )
            )

        logs = get_logs(ctx.guild.id)

        mod_log = logs[0] if logs else None

        set_log_channel(
            ctx.guild.id,
            mod_log=mod_log,
            bot_log=channel.id
        )

        await ctx.send(
            embed=success_embed(
                f"Bot logs set to {channel.mention}"
            )
        )

    # =========================
    # VIEW LOG SETTINGS
    # =========================
    @commands.hybrid_command(
        name="log_settings",
        help="View current logging setup.",
        extras={
            "example": "!log_settings",
            "tips": "Useful for checking active log channels."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def log_settings(
        self,
        ctx
    ):
        """View current logging configuration."""

        logs = get_logs(ctx.guild.id)

        mod_log = "Not set"
        bot_log = "Not set"

        if logs:

            if logs[0]:
                mod_log = f"<#{logs[0]}>"

            if logs[1]:
                bot_log = f"<#{logs[1]}>"

        embed = discord.Embed(
            title="📁 Logging Settings",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🛠️ Moderation Logs",
            value=mod_log,
            inline=False
        )

        embed.add_field(
            name="🤖 Bot Logs",
            value=bot_log,
            inline=False
        )

        embed.add_field(
            name="📌 Available Log Types",
            value=", ".join(VALID_LOGS),
            inline=False
        )

        await ctx.send(embed=embed)

# =========================
# SETUP
# =========================
async def setup(bot):

    await bot.add_cog(LogControl(bot))
