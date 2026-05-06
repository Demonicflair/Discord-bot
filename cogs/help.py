import discord
from discord.ext import commands
from discord import app_commands
import difflib

# =========================
# CONFIG
# =========================
CATEGORY_EMOJIS = {
    "Moderation": "🔨",
    "Security": "🛡️",
    "AntiNuke": "💣",
    "Tickets": "🎫",
    "Other": "⚙️"
}

recent_usage = {}  # user_id -> [commands]


def loading_embed(text="🪄 Loading..."):
    return discord.Embed(description=text, color=discord.Color.blurple())


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
    # COMMAND FETCH
    # =========================
    def get_commands(self):
        data = []
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue

            desc = cmd.help or (cmd.callback.__doc__ or "No description provided.")

            data.append({
                "name": cmd.name,
                "desc": desc,
                "usage": cmd.signature or "",
                "cog": cmd.cog_name or "Other",
                "cmd": cmd
            })
        return data

    def build_categories(self):
        cats = {}
        for cmd in self.commands_data:
            cats.setdefault(cmd["cog"], []).append(cmd)
        return cats or {"Other": []}

    # =========================
    # EMBED
    # =========================
    def build_embed(self):
        cmds = self.categories.get(self.current_category, [])
        emoji = CATEGORY_EMOJIS.get(self.current_category, "⚙️")

        start = self.page * 5
        end = start + 5
        page_cmds = cmds[start:end]

        desc = ""
        for c in page_cmds:
            desc += f"**/{c['name']}** `{c['usage']}`\n> {c['desc']}\n\n"

        return discord.Embed(
            title=f"{emoji} {self.current_category} (Page {self.page+1})",
            description=desc or "No commands",
            color=discord.Color.blurple()
        )

    # =========================
    # COMMAND DETAIL
    # =========================
    def build_command_embed(self, cmd):
        desc = cmd.help or (cmd.callback.__doc__ or "No description")

        perms = []
        for check in cmd.checks:
            if hasattr(check, "__closure__"):
                for cell in check.__closure__ or []:
                    if isinstance(cell.cell_contents, dict):
                        perms.extend(cell.cell_contents.keys())

        perms = ", ".join(perms) if perms else "None"

        cooldown = "None"
        if cmd._buckets and cmd._buckets._cooldown:
            cd = cmd._buckets._cooldown
            cooldown = f"{cd.rate}/{cd.per}s"

        example = getattr(cmd, "extras", {}).get("example", "No example")
        tips = getattr(cmd, "extras", {}).get("tips", "No tips")

        embed = discord.Embed(
            title=f"🔎 /{cmd.name}",
            description=desc,
            color=discord.Color.blurple()
        )

        embed.add_field(name="⚙️ Syntax", value=f"`/{cmd.name} {cmd.signature}`", inline=False)
        embed.add_field(name="🔐 Permissions", value=perms)
        embed.add_field(name="⏱️ Cooldown", value=cooldown)

        embed.add_field(name="💡 Example", value=f"`{example}`", inline=False)
        embed.add_field(name="🧠 Tips", value=tips, inline=False)

        return embed

    # =========================
    # SMART SEARCH
    # =========================
    def smart_search(self, query):
        names = [c["name"] for c in self.commands_data]
        matches = difflib.get_close_matches(query, names, n=3, cutoff=0.4)
        return matches

    # =========================
    # UI
    # =========================
    def refresh_ui(self):
        self.clear_items()

        # CATEGORY SELECT
        select = discord.ui.Select(
            placeholder="📚 Categories",
            options=[
                discord.SelectOption(label=name, value=name, emoji=CATEGORY_EMOJIS.get(name, "⚙️"))
                for name in self.categories
            ]
        )

        async def select_callback(interaction):
            self.current_category = select.values[0]
            self.page = 0
            self.refresh_ui()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        select.callback = select_callback
        self.add_item(select)

        # COMMAND BUTTONS
        cmds = self.categories.get(self.current_category, [])
        for c in cmds[self.page*5:self.page*5+5]:
            btn = discord.ui.Button(label=c["name"], style=discord.ButtonStyle.gray)

            async def callback(interaction, cmd=c["cmd"]):
                user_id = interaction.user.id

                recent_usage.setdefault(user_id, [])
                recent_usage[user_id].append(cmd.name)
                recent_usage[user_id] = recent_usage[user_id][-5:]

                embed = self.build_command_embed(cmd)
                await interaction.response.send_message(embed=embed, ephemeral=True)

            btn.callback = callback
            self.add_item(btn)

        self.add_item(self.prev_btn())
        self.add_item(self.next_btn())
        self.add_item(self.search_btn())
        self.add_item(self.recent_btn())

    # =========================
    # BUTTONS
    # =========================
    def prev_btn(self):
        btn = discord.ui.Button(label="⬅️", style=discord.ButtonStyle.gray)

        async def callback(interaction):
            if self.page > 0:
                self.page -= 1
                self.refresh_ui()
                await interaction.response.edit_message(embed=self.build_embed(), view=self)

        btn.callback = callback
        return btn

    def next_btn(self):
        btn = discord.ui.Button(label="➡️", style=discord.ButtonStyle.gray)

        async def callback(interaction):
            self.page += 1
            self.refresh_ui()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        btn.callback = callback
        return btn

    def search_btn(self):
        btn = discord.ui.Button(label="🔎 Search", style=discord.ButtonStyle.blurple)

        async def callback(interaction):
            await interaction.response.send_modal(SearchModal(self))

        btn.callback = callback
        return btn

    def recent_btn(self):
        btn = discord.ui.Button(label="🕘 Recent", style=discord.ButtonStyle.gray)

        async def callback(interaction):
            user_id = interaction.user.id
            cmds = recent_usage.get(user_id, [])

            if not cmds:
                return await interaction.response.send_message("No recent commands", ephemeral=True)

            text = "\n".join(f"• {c}" for c in cmds)
            await interaction.response.send_message(f"Recent:\n{text}", ephemeral=True)

        btn.callback = callback
        return btn


# =========================
# SEARCH MODAL
# =========================
class SearchModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="Search Command")
        self.view = view

        self.query = discord.ui.TextInput(label="Command name")
        self.add_item(self.query)

    async def on_submit(self, interaction):
        q = self.query.value.lower()

        for c in self.view.commands_data:
            if q == c["name"]:
                embed = self.view.build_command_embed(c["cmd"])
                return await interaction.response.send_message(embed=embed, ephemeral=True)

        matches = self.view.smart_search(q)

        if matches:
            suggestion = ", ".join(matches)
            return await interaction.response.send_message(
                f"❌ Not found. Did you mean: **{suggestion}**?",
                ephemeral=True
            )

        await interaction.response.send_message("❌ No similar commands found", ephemeral=True)


# =========================
# COG
# =========================
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help")
    @app_commands.describe(command="Command name")
    async def help_command(self, ctx, command: str = None):

        if command:
            cmd = self.bot.get_command(command)

            if cmd:
                view = HelpView(self.bot, ctx)
                embed = view.build_command_embed(cmd)
                return await ctx.send(embed=embed)

            # SMART SUGGESTION
            names = [c.name for c in self.bot.commands]
            matches = difflib.get_close_matches(command, names, n=3, cutoff=0.4)

            if matches:
                return await ctx.send(f"❌ Command not found. Did you mean: {', '.join(matches)}?")

            return await ctx.send("❌ Command not found")

        view = HelpView(self.bot, ctx)

        if ctx.interaction:
            await ctx.interaction.response.send_message(
                embed=loading_embed("🪄 Opening help..."),
                ephemeral=True
            )
            msg = await ctx.interaction.original_response()
        else:
            msg = await ctx.send(embed=loading_embed("🪄 Opening help..."))

        await msg.edit(embed=view.build_embed(), view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))
