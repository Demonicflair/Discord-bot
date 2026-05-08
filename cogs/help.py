import discord
from discord.ext import commands
from discord import app_commands
import difflib
import inspect

# =========================
# CONFIG
# =========================
CATEGORY_EMOJIS = {
    "Moderation": "🔨",
    "Security": "🛡️",
    "AntiNuke": "💣",
    "Tickets": "🎫",
    "Help": "📚",
    "Other": "⚙️"
}

recent_usage = {}


# =========================
# HELPERS
# =========================
def loading_embed(text="🪄 Loading..."):
    return discord.Embed(
        description=text,
        color=discord.Color.blurple()
    )


def get_command_description(cmd):

    if cmd.help:
        return cmd.help.strip()

    if cmd.description:
        return cmd.description.strip()

    if cmd.callback.__doc__:
        return inspect.cleandoc(cmd.callback.__doc__)

    return "No description set."


def get_permissions(cmd):

    perms = []

    for check in cmd.checks:

        if hasattr(check, "__closure__") and check.__closure__:

            for cell in check.__closure__:

                try:
                    value = cell.cell_contents

                    if isinstance(value, dict):
                        perms.extend(value.keys())

                except:
                    pass

    return perms or ["None"]


def get_cooldown(cmd):

    try:
        if cmd._buckets and cmd._buckets._cooldown:

            cd = cmd._buckets._cooldown

            return f"{cd.rate} use(s) / {cd.per}s"

    except:
        pass

    return "None"


# =========================
# HELP VIEW
# =========================
class HelpView(discord.ui.View):

    def __init__(self, bot, ctx):
        super().__init__(timeout=180)

        self.bot = bot
        self.ctx = ctx

        self.page = 0

        self.commands_data = self.get_commands()

        self.categories = self.build_categories()

        self.current_category = list(self.categories.keys())[0]

        self.refresh_ui()

    # =========================
    # FETCH COMMANDS
    # =========================
    def get_commands(self):

        data = []

        for cmd in sorted(self.bot.commands, key=lambda c: c.name):

            if cmd.hidden:
                continue

            desc = get_command_description(cmd)

            data.append({
                "name": cmd.name,
                "desc": desc,
                "usage": cmd.signature or "No arguments",
                "aliases": cmd.aliases or [],
                "cooldown": get_cooldown(cmd),
                "permissions": get_permissions(cmd),
                "cog": cmd.cog_name or "Other",
                "cmd": cmd
            })

        return data

    # =========================
    # BUILD CATEGORIES
    # =========================
    def build_categories(self):

        cats = {}

        for cmd in self.commands_data:

            cats.setdefault(cmd["cog"], []).append(cmd)

        return cats or {"Other": []}

    # =========================
    # MAIN EMBED
    # =========================
    def build_embed(self):

        cmds = self.categories.get(self.current_category, [])

        emoji = CATEGORY_EMOJIS.get(
            self.current_category,
            "⚙️"
        )

        per_page = 5

        max_pages = max(1, (len(cmds)-1)//per_page + 1)

        if self.page >= max_pages:
            self.page = max_pages - 1

        start = self.page * per_page
        end = start + per_page

        page_cmds = cmds[start:end]

        embed = discord.Embed(
            title=f"{emoji} {self.current_category}",
            description=(
                f"📄 Page {self.page+1}/{max_pages}\n"
                f"Use `!help <command>` for details."
            ),
            color=discord.Color.blurple()
        )

        for c in page_cmds:

            embed.add_field(
                name=f"🔹 {c['name']}",
                value=(
                    f"> {c['desc'][:120]}\n"
                    f"`!{c['name']} {c['usage']}`"
                ),
                inline=False
            )

        embed.set_footer(
            text=f"{len(cmds)} commands"
        )

        return embed

    # =========================
    # COMMAND EMBED
    # =========================
    def build_command_embed(self, cmd):

        desc = get_command_description(cmd)

        perms = ", ".join(get_permissions(cmd))

        cooldown = get_cooldown(cmd)

        aliases = ", ".join(cmd.aliases) if cmd.aliases else "None"

        example = getattr(
            cmd,
            "example",
            f"!{cmd.name}"
        )

        tips = getattr(
            cmd,
            "tips",
            "No tips available."
        )

        embed = discord.Embed(
            title=f"🔎 Command: {cmd.name}",
            description=desc,
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="⚙️ Prefix Syntax",
            value=f"`!{cmd.name} {cmd.signature}`",
            inline=False
        )

        embed.add_field(
            name="⚡ Slash Syntax",
            value=f"`/{cmd.name}`",
            inline=False
        )

        embed.add_field(
            name="🔐 Permissions",
            value=perms,
            inline=True
        )

        embed.add_field(
            name="⏱️ Cooldown",
            value=cooldown,
            inline=True
        )

        embed.add_field(
            name="📚 Aliases",
            value=aliases,
            inline=False
        )

        embed.add_field(
            name="💡 Example",
            value=f"`{example}`",
            inline=False
        )

        embed.add_field(
            name="🧠 Tips",
            value=tips,
            inline=False
        )

        return embed

    # =========================
    # SEARCH
    # =========================
    def smart_search(self, query):

        names = [c["name"] for c in self.commands_data]

        return difflib.get_close_matches(
            query,
            names,
            n=5,
            cutoff=0.35
        )

    # =========================
    # UI
    # =========================
    def refresh_ui(self):

        self.clear_items()

        # CATEGORY SELECT
        select = discord.ui.Select(
            placeholder="📚 Select Category",
            options=[
                discord.SelectOption(
                    label=name,
                    value=name,
                    emoji=CATEGORY_EMOJIS.get(name, "⚙️")
                )
                for name in self.categories
            ]
        )

        async def select_callback(interaction):

            self.current_category = select.values[0]

            self.page = 0

            self.refresh_ui()

            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self
            )

        select.callback = select_callback

        self.add_item(select)

        # NAVIGATION
        self.add_item(self.prev_btn())
        self.add_item(self.next_btn())
        self.add_item(self.search_btn())
        self.add_item(self.recent_btn())

    # =========================
    # BUTTONS
    # =========================
    def prev_btn(self):

        btn = discord.ui.Button(
            label="⬅️",
            style=discord.ButtonStyle.gray
        )

        async def callback(interaction):

            if self.page > 0:

                self.page -= 1

                self.refresh_ui()

                await interaction.response.edit_message(
                    embed=self.build_embed(),
                    view=self
                )

        btn.callback = callback

        return btn

    def next_btn(self):

        btn = discord.ui.Button(
            label="➡️",
            style=discord.ButtonStyle.gray
        )

        async def callback(interaction):

            cmds = self.categories.get(
                self.current_category,
                []
            )

            max_pages = max(
                1,
                (len(cmds)-1)//5 + 1
            )

            if self.page + 1 < max_pages:

                self.page += 1

                self.refresh_ui()

                await interaction.response.edit_message(
                    embed=self.build_embed(),
                    view=self
                )

        btn.callback = callback

        return btn

    def search_btn(self):

        btn = discord.ui.Button(
            label="🔎 Search",
            style=discord.ButtonStyle.blurple
        )

        async def callback(interaction):

            await interaction.response.send_modal(
                SearchModal(self)
            )

        btn.callback = callback

        return btn

    def recent_btn(self):

        btn = discord.ui.Button(
            label="🕘 Recent",
            style=discord.ButtonStyle.gray
        )

        async def callback(interaction):

            user_id = interaction.user.id

            cmds = recent_usage.get(user_id, [])

            if not cmds:

                return await interaction.response.send_message(
                    "No recent commands.",
                    ephemeral=True
                )

            text = "\n".join(
                f"• {c}" for c in cmds[-10:]
            )

            embed = discord.Embed(
                title="🕘 Recently Viewed",
                description=text,
                color=discord.Color.blurple()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        btn.callback = callback

        return btn


# =========================
# SEARCH MODAL
# =========================
class SearchModal(discord.ui.Modal):

    def __init__(self, view):

        super().__init__(title="Search Command")

        self.view = view

        self.query = discord.ui.TextInput(
            label="Command Name"
        )

        self.add_item(self.query)

    async def on_submit(self, interaction):

        q = self.query.value.lower()

        for c in self.view.commands_data:

            if q == c["name"]:

                recent_usage.setdefault(
                    interaction.user.id,
                    []
                )

                recent_usage[interaction.user.id].append(
                    c["name"]
                )

                embed = self.view.build_command_embed(
                    c["cmd"]
                )

                return await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True
                )

        matches = self.view.smart_search(q)

        if matches:

            return await interaction.response.send_message(
                f"❌ Command not found.\nDid you mean:\n`{' , '.join(matches)}`",
                ephemeral=True
            )

        await interaction.response.send_message(
            "❌ No similar commands found.",
            ephemeral=True
        )


# =========================
# HELP COG
# =========================
class Help(commands.Cog):
    """
    Advanced interactive help system.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="help",
        description="View all bot commands"
    )
    @app_commands.describe(
        command="Specific command name"
    )
    async def help_command(
        self,
        ctx,
        command: str = None
    ):
        """
        Open the interactive help menu.

        Examples:
        !help
        !help ban
        /help
        """

        # =========================
        # SPECIFIC COMMAND
        # =========================
        if command:

            cmd = self.bot.get_command(command)

            if cmd:

                recent_usage.setdefault(
                    ctx.author.id,
                    []
                )

                recent_usage[ctx.author.id].append(
                    cmd.name
                )

                view = HelpView(self.bot, ctx)

                embed = view.build_command_embed(cmd)

                return await ctx.send(embed=embed)

            names = [c.name for c in self.bot.commands]

            matches = difflib.get_close_matches(
                command,
                names,
                n=5,
                cutoff=0.35
            )

            if matches:

                return await ctx.send(
                    f"❌ Command not found.\nDid you mean:\n`{' , '.join(matches)}`"
                )

            return await ctx.send(
                "❌ Command not found."
            )

        # =========================
        # MAIN HELP
        # =========================
        view = HelpView(self.bot, ctx)

        if ctx.interaction:

            await ctx.interaction.response.send_message(
                embed=loading_embed(
                    "🪄 Opening Help Menu..."
                ),
                ephemeral=True
            )

            msg = await ctx.interaction.original_response()

        else:

            msg = await ctx.send(
                embed=loading_embed(
                    "🪄 Opening Help Menu..."
                )
            )

        await msg.edit(
            embed=view.build_embed(),
            view=view
        )


async def setup(bot):
    await bot.add_cog(Help(bot))
