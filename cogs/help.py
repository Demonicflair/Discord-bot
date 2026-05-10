
import discord
from discord.ext import commands
from discord import app_commands

BRAND_COLOR = 0x2b2d31

# =========================
# 🎨 THE DROPDOWN MENU
# =========================
class HelpDropdown(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="Security & Anti-Nuke", description="Shields and AI protection", emoji="🛡️"),
            discord.SelectOption(label="Moderation", description="Hammer and staff tools", emoji="🔨"),
            discord.SelectOption(label="Tickets & Support", description="Help desk system", emoji="🎫"),
            discord.SelectOption(label="Utility & Welcome", description="General tools and greets", emoji="⚙️"),
        ]
        super().__init__(placeholder="Choose a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = discord.Embed(title=f"{category} Commands", color=BRAND_COLOR)
        
        # Categorizing the help based on our cogs
        if category == "Security & Anti-Nuke":
            embed.description = (
                "**`!antinuke whitelist`** - Add a safe user\n"
                "**`!security status`** - Check user AI heat\n"
                "**`!security reset`** - Clear user AI score"
            )
        elif category == "Moderation":
            embed.description = (
                "**`!ban`** / **`!kick`** - Remove members\n"
                "**`!warn`** - Add a strike\n"
                "**`!clear`** - Purge messages\n"
                "**`!history`** - View user logs"
            )
        elif category == "Tickets & Support":
            embed.description = (
                "**`!ticket setup`** - Create support panel\n"
                "**`!ticket blacklist`** - Block from tickets"
            )
        elif category == "Utility & Welcome":
            embed.description = (
                "**`!userinfo`** - View profile card\n"
                "**`!serverinfo`** - View guild stats\n"
                "**`!afk`** - Set away status\n"
                "**`!welcome setup`** - Configure greets"
            )

        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.add_item(HelpDropdown(bot))

# =========================
# 📖 THE HELP COG
# =========================
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="📖 Open the interactive help menu.")
    async def help(self, ctx):
        embed = discord.Embed(
            title="Dem Security • Help Menu",
            description=(
                "Welcome to the **Dem System**. Use the dropdown menu below "
                "to explore commands by category.\n\n"
                "**Prefix:** `!` | **Slash Commands:** Enabled"
            ),
            color=BRAND_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Developed for Elite Servers")
        
        await ctx.send(embed=embed, view=HelpView(self.bot))

async def setup(bot):
    await bot.add_cog(Help(bot))
