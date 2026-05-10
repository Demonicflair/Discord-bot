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
    "AntiNuke": "🔒",
    "Tickets": "🎫",
    "Help": "📚",
    "Leveling": "🆙",
    "Utility": "⚙️",
    "Other": "🧩"
}

recent_usage = {}

def get_command_description(cmd):
    if cmd.help: return cmd.help.strip()
    if cmd.description: return cmd.description.strip()
    return "No description available."

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

    def get_commands(self):
        data = []
        for cmd in sorted(self.bot.commands, key=lambda c: c.name):
            if cmd.hidden: continue
            data.append({
                "name": cmd.name,
                "desc": get_command_description(cmd),
                "usage": cmd.signature or "",
                "cog": cmd.cog_name or "Other",
                "cmd": cmd
            })
        return data

    def build_categories(self):
        cats = {}
        for cmd in self.commands_data:
            cats.setdefault(cmd["cog"], []).append(cmd)
        return cats

    def build_embed(self):
        cmds = self.categories.get(self.current_category, [])
        emoji = CATEGORY_EMOJIS.get(self.current_category, "⚙️")
        
        per_page = 5
        max_pages = max(1, (len(cmds)-1)//per_page + 1)
        self.page = min(self.page, max_pages - 1)

        start = self.page * per_page
        page_cmds = cmds[start:start + per_page]

        embed = discord.Embed(
            title=f"{emoji} {self.current_category} Commands",
            description=f"Explore the {self.current_category} module commands below.\nPage **{self.page+1}/{max_pages}**",
            color=0x2b2d31
        )

        for c in page_cmds:
            embed.add_field(
                name=f"🔹 {c['name']}",
                value=f"> {c['desc'][:100]}\n`!{c['name']} {c['usage']}`",
                inline=False
            )

        embed.set_footer(text=f"Total: {len(cmds)} commands | Requested by {self.ctx.author}")
        return embed

    def refresh_ui(self):
        self.clear_items()
        
        # Category Select Menu
        select = discord.ui.Select(
            placeholder="Choose a category...",
            options=[
                discord.SelectOption(
                    label=name, 
                    value=name, 
                    emoji=CATEGORY_EMOJIS.get(name, "⚙️"),
                    description=f"{len(cmds)} commands available"
                ) for name, cmds in self.categories.items()
            ]
        )

        async def select_callback(interaction):
            if interaction.user.id != self.ctx.author.id:
                return await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
            self.current_category = select.values[0]
            self.page = 0
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

        select.callback = select_callback
        self.add_item(select)

        # Nav Buttons
        self.add_item(self.nav_button("⬅️", -1))
        self.add_item(self.nav_button("➡️", 1))

    def nav_button(self, label, delta):
        btn = discord.ui.Button(label=label, style=discord.ButtonStyle.gray)
        async def callback(interaction):
            if interaction.user.id != self.ctx.author.id: return
            self.page += delta
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
        btn.callback = callback
        return btn

# =========================
# HELP COG
# =========================
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", description="The ultimate guide to Dem's features.")
    @app_commands.describe(command="Specific command to look up")
    async def help_command(self, ctx, command: str = None):
        if command:
            cmd = self.bot.get_command(command.lower())
            if not cmd:
                # Smart Match logic
                matches = difflib.get_close_matches(command, [c.name for c in self.bot.commands], n=3, cutoff=0.5)
                msg = f"❌ Command `{command}` not found."
                if matches: msg += f"\nDid you mean: `{'`, `'.join(matches)}`?"
                return await ctx.send(msg)

            # Build Detailed Command Embed
            embed = discord.Embed(title=f"🔎 Command: {cmd.name}", description=get_command_description(cmd), color=0x2b2d31)
            embed.add_field(name="Syntax", value=f"`!{cmd.name} {cmd.signature}`\n`/{cmd.name}`", inline=False)
            if cmd.aliases: embed.add_field(name="Aliases", value=", ".join(cmd.aliases), inline=True)
            
            return await ctx.send(embed=embed)

        # Main Interactive Help
        view = HelpView(self.bot, ctx)
        await ctx.send(embed=view.build_embed(), view=view)

    # Elite: Slash Command Auto-complete for /help command:
    @help_command.autocomplete("command")
    async def help_autocomplete(self, interaction: discord.Interaction, current: str):
        commands_list = [c.name for c in self.bot.commands if not c.hidden]
        return [
            app_commands.Choice(name=cmd, value=cmd)
            for cmd in commands_list if current.lower() in cmd.lower()
        ][:25]

async def setup(bot):
    await bot.add_cog(Help(bot))
