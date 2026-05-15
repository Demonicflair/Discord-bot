import discord
from discord.ext import commands
from discord import app_commands

from utils.config import BRAND_COLOR, PREFIX


# =========================
# HELP DROPDOWN
# =========================
class HelpDropdown(discord.ui.Select):

    def __init__(self, bot):

        self.bot = bot

        options = [

            discord.SelectOption(
                label="Security System",
                description="AI protection, anti raid and server defense",
                emoji="🛡️"
            ),

            discord.SelectOption(
                label="Moderation",
                description="Powerful staff and punishment commands",
                emoji="🔨"
            ),

            discord.SelectOption(
                label="Tickets & Support",
                description="Advanced support ticket management",
                emoji="🎫"
            ),

            discord.SelectOption(
                label="Utility",
                description="Useful daily tools and server utilities",
                emoji="⚙️"
            ),

            discord.SelectOption(
                label="Welcome & Automation",
                description="Automatic welcomes, roles and greetings",
                emoji="👋"
            ),

            discord.SelectOption(
                label="Giveaways",
                description="Host professional giveaways and events",
                emoji="🎉"
            )
        ]

        super().__init__(
            placeholder="Select a command category...",
            min_values=1,
            max_values=1,
            options=options
        )

    # =========================
    # DROPDOWN CALLBACK
    # =========================
    async def callback(self, interaction: discord.Interaction):

        category = self.values[0]

        embed = discord.Embed(
            color=BRAND_COLOR
        )

        # =========================
        # SECURITY
        # =========================
        if category == "Security System":

            embed.title = "🛡️ Security & Protection"

            embed.description = (
                "Protect your server using Dem's intelligent "
                "security systems, scam detection and automated moderation."
            )

            embed.add_field(
                name="⚡ Main Commands",
                value=(
                    f"`{PREFIX}security status` → Check AI heat level\n"
                    f"`{PREFIX}security reset` → Reset user security heat\n"
                    f"`{PREFIX}log_enable` → Enable security logs\n"
                    f"`{PREFIX}log_disable` → Disable security logs"
                ),
                inline=False
            )

            embed.add_field(
                name="🧠 Features",
                value=(
                    "• Scam & phishing detection\n"
                    "• Mass mention protection\n"
                    "• AI heat system\n"
                    "• Auto punishments\n"
                    "• Security logging"
                ),
                inline=False
            )

        # =========================
        # MODERATION
        # =========================
        elif category == "Moderation":

            embed.title = "🔨 Moderation Commands"

            embed.description = (
                "Everything your staff team needs to manage "
                "members quickly and professionally."
            )

            embed.add_field(
                name="🛠️ Punishment Commands",
                value=(
                    f"`{PREFIX}ban` → Permanently ban a member\n"
                    f"`{PREFIX}kick` → Remove a member from the server\n"
                    f"`{PREFIX}warn` → Add a warning strike\n"
                    f"`{PREFIX}clear` → Bulk delete messages"
                ),
                inline=False
            )

            embed.add_field(
                name="📋 Investigation",
                value=(
                    f"`{PREFIX}history` → View moderation history\n"
                    f"`{PREFIX}mod_stats` → Server moderation stats"
                ),
                inline=False
            )

        # =========================
        # TICKETS
        # =========================
        elif category == "Tickets & Support":

            embed.title = "🎫 Ticket System"

            embed.description = (
                "A clean and modern support system "
                "for staff and members."
            )

            embed.add_field(
                name="📩 Ticket Commands",
                value=(
                    f"`{PREFIX}ticket setup` → Create ticket panel\n"
                    f"`{PREFIX}ticket blacklist` → Block ticket access"
                ),
                inline=False
            )

            embed.add_field(
                name="✨ Features",
                value=(
                    "• Persistent buttons\n"
                    "• Private support channels\n"
                    "• Auto ticket management\n"
                    "• Blacklist system\n"
                    "• Staff friendly workflow"
                ),
                inline=False
            )

        # =========================
        # UTILITY
        # =========================
        elif category == "Utility":

            embed.title = "⚙️ Utility Commands"

            embed.description = (
                "Helpful commands designed for everyday server usage."
            )

            embed.add_field(
                name="🧰 Commands",
                value=(
                    f"`{PREFIX}afk` → Set an AFK status\n"
                    f"`{PREFIX}help` → Open help menu\n"
                    f"`{PREFIX}setuplogs` → Setup logging channels\n"
                    f"`{PREFIX}log_settings` → View log configuration"
                ),
                inline=False
            )

        # =========================
        # WELCOME
        # =========================
        elif category == "Welcome & Automation":

            embed.title = "👋 Welcome System"

            embed.description = (
                "Automatically greet new members and "
                "improve your server onboarding."
            )

            embed.add_field(
                name="🏠 Welcome Commands",
                value=(
                    f"`{PREFIX}welcome setup` → Setup welcome channel\n"
                    f"`{PREFIX}welcome msg` → Customize join message"
                ),
                inline=False
            )

            embed.add_field(
                name="🤖 Automation",
                value=(
                    "• Auto role system\n"
                    "• Custom placeholders\n"
                    "• Embed welcomes\n"
                    "• Join & leave support"
                ),
                inline=False
            )

        # =========================
        # GIVEAWAYS
        # =========================
        elif category == "Giveaways":

            embed.title = "🎉 Giveaway System"

            embed.description = (
                "Run advanced giveaways with requirements, "
                "blacklists and automatic winner selection."
            )

            embed.add_field(
                name="🎁 Giveaway Commands",
                value=(
                    f"`{PREFIX}gstart` → Start a giveaway\n"
                    f"`{PREFIX}glist` → View active giveaways"
                ),
                inline=False
            )

            embed.add_field(
                name="🏆 Features",
                value=(
                    "• Auto winner selection\n"
                    "• Role requirements\n"
                    "• Blacklisted roles\n"
                    "• Persistent buttons\n"
                    "• Giveaway reminders"
                ),
                inline=False
            )

        # =========================
        # UNIVERSAL FOOTER
        # =========================
        embed.set_footer(
            text="Dem Security • Advanced Discord Protection"
        )

        embed.set_thumbnail(
            url=self.bot.user.display_avatar.url
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self.view
        )


# =========================
# HELP VIEW
# =========================
class HelpView(discord.ui.View):

    def __init__(self, bot):

        super().__init__(timeout=180)

        self.add_item(HelpDropdown(bot))


# =========================
# HELP COG
# =========================
class Help(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # HELP COMMAND
    # =========================
    @commands.hybrid_command(
        name="help",
        description="Open the interactive help menu."
    )
    async def help(self, ctx):

        embed = discord.Embed(
            title="🛡️ Dem Security",
            description=(
                "Welcome to **Dem Security**, an advanced moderation "
                "and protection system built for modern Discord servers.\n\n"

                "Use the dropdown menu below to explore commands, "
                "features and server systems.\n\n"

                f"**Prefix:** `{PREFIX}`\n"
                "**Slash Commands:** Enabled\n"
                "**System Status:** Online"
            ),
            color=BRAND_COLOR
        )

        embed.add_field(
            name="🚀 Main Features",
            value=(
                "• AI Security System\n"
                "• Advanced Moderation\n"
                "• Ticket Management\n"
                "• Giveaway System\n"
                "• Smart Logging\n"
                "• Welcome Automation"
            ),
            inline=False
        )

        embed.add_field(
            name="📌 Quick Start",
            value=(
                f"`{PREFIX}setuplogs` → Setup logging system\n"
                f"`{PREFIX}ticket setup` → Setup ticket system\n"
                f"`{PREFIX}welcome setup` → Configure welcomes"
            ),
            inline=False
        )

        embed.set_thumbnail(
            url=self.bot.user.display_avatar.url
        )

        embed.set_footer(
            text="Dem Security • Built for Professional Communities"
        )

        await ctx.send(
            embed=embed,
            view=HelpView(self.bot)
        )


# =========================
# LOAD COG
# =========================
async def setup(bot):

    await bot.add_cog(Help(bot))
