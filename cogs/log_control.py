import discord
from discord.ext import commands
from discord import app_commands
import traceback

from utils.logger import (
    set_log_state,
    set_log_channels,
    get_logs,
    is_log_enabled
)

# =========================
# CONFIG
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

DEM_COLOR = 0x2b2d31


# =========================
# EMBED HELPER
# =========================

def build_embed(
    description,
    success=True
):

    return discord.Embed(
        description=f"{'✅' if success else '❌'} {description}",
        color=(
            discord.Color.green()
            if success
            else discord.Color.red()
        )
    )


# =========================
# LOG CONTROL COG
# =========================

class LogControl(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # SAFE SEND
    # =========================

    async def safe_send(
        self,
        ctx,
        embed
    ):

        try:

            if ctx.interaction:

                if ctx.interaction.response.is_done():

                    await ctx.followup.send(
                        embed=embed,
                        ephemeral=True
                    )

                else:

                    await ctx.interaction.response.send_message(
                        embed=embed,
                        ephemeral=True
                    )

            else:

                await ctx.send(
                    embed=embed
                )

        except Exception:

            traceback.print_exc()

    # =========================
    # AUTOCOMPLETE
    # =========================

    async def log_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):

        return [

            app_commands.Choice(
                name=log,
                value=log
            )

            for log in VALID_LOGS

            if current.lower() in log.lower()

        ][:25]

    # =========================
    # ENABLE LOG
    # =========================

    @commands.hybrid_command(
        name="log_enable",
        description="Enable a specific log type."
    )
    @commands.has_permissions(
        manage_guild=True
    )
    async def log_enable(
        self,
        ctx,
        log_type: str
    ):

        try:

            log_type = log_type.lower()

            if log_type not in VALID_LOGS:

                return await self.safe_send(
                    ctx,
                    build_embed(
                        "Invalid log type.",
                        False
                    )
                )

            await set_log_state(
                ctx.guild.id,
                log_type,
                True
            )

            await self.safe_send(
                ctx,
                build_embed(
                    f"Enabled `{log_type}` logs."
                )
            )

        except Exception:

            traceback.print_exc()

            await self.safe_send(
                ctx,
                build_embed(
                    "Failed to enable logs.",
                    False
                )
            )

    @log_enable.autocomplete("log_type")
    async def log_enable_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):

        return await self.log_autocomplete(
            interaction,
            current
        )

    # =========================
    # DISABLE LOG
    # =========================

    @commands.hybrid_command(
        name="log_disable",
        description="Disable a specific log type."
    )
    @commands.has_permissions(
        manage_guild=True
    )
    async def log_disable(
        self,
        ctx,
        log_type: str
    ):

        try:

            log_type = log_type.lower()

            if log_type not in VALID_LOGS:

                return await self.safe_send(
                    ctx,
                    build_embed(
                        "Invalid log type.",
                        False
                    )
                )

            await set_log_state(
                ctx.guild.id,
                log_type,
                False
            )

            await self.safe_send(
                ctx,
                build_embed(
                    f"Disabled `{log_type}` logs."
                )
            )

        except Exception:

            traceback.print_exc()

            await self.safe_send(
                ctx,
                build_embed(
                    "Failed to disable logs.",
                    False
                )
            )

    @log_disable.autocomplete("log_type")
    async def log_disable_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):

        return await self.log_autocomplete(
            interaction,
            current
        )

    # =========================
    # SET MOD LOG
    # =========================

    @commands.hybrid_command(
        name="set_modlog",
        description="Set moderation log channel."
    )
    @commands.has_permissions(
        manage_guild=True
    )
    async def set_modlog(
        self,
        ctx,
        channel: discord.TextChannel
    ):

        try:

            perms = channel.permissions_for(
                ctx.guild.me
            )

            if not perms.send_messages:

                return await self.safe_send(
                    ctx,
                    build_embed(
                        "I cannot send messages there.",
                        False
                    )
                )

            logs = await get_logs(
                ctx.guild.id
            )

            bot_log = (
                logs[1]
                if logs
                else None
            )

            await set_log_channels(
                ctx.guild.id,
                mod_log=channel.id,
                bot_log=bot_log
            )

            await self.safe_send(
                ctx,
                build_embed(
                    f"Moderation logs set to {channel.mention}"
                )
            )

        except Exception:

            traceback.print_exc()

            await self.safe_send(
                ctx,
                build_embed(
                    "Failed to set moderation logs.",
                    False
                )
            )

    # =========================
    # SET BOT LOG
    # =========================

    @commands.hybrid_command(
        name="set_botlog",
        description="Set bot/system log channel."
    )
    @commands.has_permissions(
        manage_guild=True
    )
    async def set_botlog(
        self,
        ctx,
        channel: discord.TextChannel
    ):

        try:

            perms = channel.permissions_for(
                ctx.guild.me
            )

            if not perms.send_messages:

                return await self.safe_send(
                    ctx,
                    build_embed(
                        "I cannot send messages there.",
                        False
                    )
                )

            logs = await get_logs(
                ctx.guild.id
            )

            mod_log = (
                logs[0]
                if logs
                else None
            )

            await set_log_channels(
                ctx.guild.id,
                mod_log=mod_log,
                bot_log=channel.id
            )

            await self.safe_send(
                ctx,
                build_embed(
                    f"Bot logs set to {channel.mention}"
                )
            )

        except Exception:

            traceback.print_exc()

            await self.safe_send(
                ctx,
                build_embed(
                    "Failed to set bot logs.",
                    False
                )
            )

    # =========================
    # VIEW SETTINGS
    # =========================

    @commands.hybrid_command(
        name="log_settings",
        description="View logging configuration."
    )
    @commands.has_permissions(
        manage_guild=True
    )
    async def log_settings(
        self,
        ctx
    ):

        try:

            logs = await get_logs(
                ctx.guild.id
            )

            mod_log = (

                f"<#{logs[0]}>"

                if logs and logs[0]

                else "`Not Set`"

            )

            bot_log = (

                f"<#{logs[1]}>"

                if logs and logs[1]

                else "`Not Set`"

            )

            embed = discord.Embed(
                title="📁 Dem Logging Configuration",
                color=DEM_COLOR
            )

            embed.add_field(
                name="🛠️ Moderation Logs",
                value=mod_log,
                inline=True
            )

            embed.add_field(
                name="🤖 Bot/System Logs",
                value=bot_log,
                inline=True
            )

            enabled_logs = []

            for log in VALID_LOGS:

                state = await is_log_enabled(
                    ctx.guild.id,
                    log
                )

                enabled_logs.append(
                    f"{'🟢' if state else '🔴'} {log}"
                )

            embed.add_field(
                name="📌 Log Status",
                value="\n".join(enabled_logs),
                inline=False
            )

            embed.set_footer(
                text="Dem Advanced Logging System"
            )

            await self.safe_send(
                ctx,
                embed
            )

        except Exception:

            traceback.print_exc()

            await self.safe_send(
                ctx,
                build_embed(
                    "Failed to fetch log settings.",
                    False
                )
            )


# =========================
# LOAD COG
# =========================

async def setup(bot):

    await bot.add_cog(
        LogControl(bot)
    )
