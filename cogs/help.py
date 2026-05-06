import discord
from discord.ext import commands

# =========================
# CATEGORY EMOJIS
# =========================
CATEGORY_EMOJIS = {
    "Moderation": "🔨",
    "Security": "🛡️",
    "Ticket": "🎫",
    "Tickets": "🎫",
    "AntiNuke": "💣",
    "Other": "⚙️"
}

# =========================
# LOADING EMBED
# =========================
def loading_embed(text="🪄 Loading..."):
    return discord.Embed(
        description=text,
        color=discord.Color.blurple()
    )

# =========================
# SEARCH MODAL
# =========================
class SearchModal(discord.ui.Modal, title="🔎 Search Command"):
    query = discord.ui.TextInput(
        label="Enter command name",
        placeholder="ban, security, ticket..."
    )

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        q = self.query.value.lower()

        # show loading animation
        await interaction.response.edit_message(embed=loading_embed("🔎 Searching..."), view=None)

        results = []
        for cmd in self.view.commands_data:
            if q in cmd["name"]:
                results.append(
                    f"**/{cmd['name']}** `{cmd['usage']}`\n> {cmd['desc']}"
                )

        desc = "\n\n".join(results[:10]) if results else "❌ No commands found."

        embed = discord.Embed(
            title=f"🔎 Results for '{q}'",
            description=desc,
            color=discord.Color.blurple()
        )

        await interaction.edit_original_response(embed=embed, view=self.view)


# =========================
# HELP VIEW
# =========================
class HelpView(discord.ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=180)
        self.bot = bot
        self.ctx = ctx
        self.commands_data = self.get_commands()
        self.categories = self.build_categories()
        self.current_category = list(self.categories.keys())[0]

    def get_commands(self):
        data = []
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue

            data.append({
                "name": cmd.name,
                "desc": cmd.help or "No description",
                "usage": cmd.signature or "",
                "cog": cmd.cog_name or "Other"
            })
        return data

    def build_categories(self):
        cats = {}
        for cmd in self.commands_data:
            cats.setdefault(cmd["cog"], []).append(cmd)
        return cats

    def build_embed(self):
        cmds = self.categories[self.current_category]
        emoji = CATEGORY_EMOJIS.get(self.current_category, "⚙️")

        desc = ""
        for c in cmds[:15]:
            desc += f"**/{c['name']}** `{c['usage']}`\n> {c['desc']}\n\n"

        embed = discord.Embed(
            title=f"{emoji} {self.current_category}",
            description=desc or "No commands",
            color=discord.Color.blurple()
        )

        embed.set_footer(text=f"{len(cmds)} commands • Use menu below")
        return embed

    # =========================
    # ANIMATION SWITCH
    # =========================
    async def switch_category(self, interaction, category):
        self.current_category = category

        await interaction.response.edit_message(embed=loading_embed(), view=None)

        await interaction.edit_original_response(
            embed=self.build_embed(),
            view=self
        )

    # =========================
    # DROPDOWN
    # =========================
    @discord.ui.select(placeholder="📚 Select category...")
    async def select_category(self, interaction, select):
        await self.switch_category(interaction, select.values[0])

    # =========================
    # BUTTONS
    # =========================
    @discord.ui.button(label="🔎 Search", style=discord.ButtonStyle.gray)
    async def search(self, interaction, button):
        await interaction.response.send_modal(SearchModal(self))

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.blurple)
    async def refresh(self, interaction, button):
        await interaction.response.edit_message(embed=loading_embed(), view=None)

        self.commands_data = self.get_commands()
        self.categories = self.build_categories()

        await interaction.edit_original_response(
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.gray)
    async def home(self, interaction, button):
        first = list(self.categories.keys())[0]
        await self.switch_category(interaction, first)


# =========================
# COG
# =========================
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help")
    async def help_command(self, ctx):
        view = HelpView(self.bot, ctx)

        view.select_category.options = [
            discord.SelectOption(
                label=name,
                value=name,
                emoji=CATEGORY_EMOJIS.get(name, "⚙️")
            )
            for name in view.categories.keys()
        ]

        msg = await ctx.send(embed=loading_embed("🪄 Opening help panel..."))

        await msg.edit(
            embed=view.build_embed(),
            view=view
        )


async def setup(bot):
    await bot.add_cog(Help(bot))
