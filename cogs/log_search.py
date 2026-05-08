from discord.ext import commands
from discord import app_commands
from utils.logger import set_log


class LogControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # ✅ ENABLE LOGS
    # =========================
    @commands.hybrid_command(
        name="log_enable",
        help="Enable a specific log type.",
        extras={
            "example": "!log_enable ban",
            "tips": (
                "Enable moderation, ticket, antinuke, "
                "security, or other logs."
            )
        }
    )
    @app_commands.describe(
        log="The log type you want to enable"
    )
    @commands.has_permissions(manage_guild=True)
    async def log_enable(
        self,
        ctx,
        log: str = None
    ):
        """Enable a specific log type."""

        if log is None:
            return await ctx.send(
                "❌ Usage: !log_enable <log_type>"
            )

        log = log.lower()

        set_log(
            ctx.guild.id,
            log,
            True
        )

        embed = (
            discord.Embed(
                title="✅ Logs Enabled",
                description=(
                    f"Successfully enabled "
                    f"`{log}` logs."
                ),
                color=discord.Color.green()
            )
        )

        embed.add_field(
            name="📘 Example",
            value="`!log_enable ban`",
            inline=False
        )

        embed.set_footer(
            text=f"Enabled by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=embed)

    # =========================
    # ❌ DISABLE LOGS
    # =========================
    @commands.hybrid_command(
        name="log_disable",
        help="Disable a specific log type.",
        extras={
            "example": "!log_disable ticket",
            "tips": (
                "Disable logs that are too spammy "
                "or unnecessary."
            )
        }
    )
    @app_commands.describe(
        log="The log type you want to disable"
    )
    @commands.has_permissions(manage_guild=True)
    async def log_disable(
        self,
        ctx,
        log: str = None
    ):
        """Disable a specific log type."""

        if log is None:
            return await ctx.send(
                "❌ Usage: !log_disable <log_type>"
            )

        log = log.lower()

        set_log(
            ctx.guild.id,
            log,
            False
        )

        embed = (
            discord.Embed(
                title="❌ Logs Disabled",
                description=(
                    f"Successfully disabled "
                    f"`{log}` logs."
                ),
                color=discord.Color.red()
            )
        )

        embed.add_field(
            name="📘 Example",
            value="`!log_disable ticket`",
            inline=False
        )

        embed.set_footer(
            text=f"Disabled by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LogControl(bot))
