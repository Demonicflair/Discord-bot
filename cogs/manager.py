import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB_PATH = "bot.db"
DEM_COLOR = 0x2b2d31

# The list of modules/features that can be toggled
TOGGLE_CHOICES = [
    app_commands.Choice(name="Anti-Nuke", value="antinuke"),
    app_commands.Choice(name="Security AI", value="security"),
    app_commands.Choice(name="Leveling System", value="leveling"),
    app_commands.Choice(name="Booster Rewards", value="booster"),
    app_commands.Choice(name="Welcome System", value="welcome"),
    app_commands.Choice(name="Ticket System", value="tickets"),
]

# =========================
# INTERACTIVE PANEL
# =========================
class ManagerPanel(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    async def update_state(self, interaction, feature):
        current = await self.cog.get_state(self.guild_id, feature)
        await self.cog.set_state(self.guild_id, feature, not current)
        
        embed = await self.cog.get_status_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Anti-Nuke", style=discord.ButtonStyle.gray)
    async def toggle_antinuke(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_state(interaction, "antinuke")

    @discord.ui.button(label="Security", style=discord.ButtonStyle.gray)
    async def toggle_security(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_state(interaction, "security")

    @discord.ui.button(label="Leveling", style=discord.ButtonStyle.gray)
    async def toggle_leveling(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_state(interaction, "leveling")

# =========================
# MANAGER COG
# =========================
class Manager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_state(self, guild_id, feature):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT enabled FROM settings WHERE guild_id=? AND feature=?", (guild_id, feature)) as cur:
                r = await cur.fetchone()
                return r is None or r[0] == 1 # Default to ON

    async def set_state(self, guild_id, feature, state):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO settings (guild_id, feature, enabled) VALUES (?, ?, ?)", 
                           (guild_id, feature, int(state)))
            await db.commit()

    async def get_status_embed(self, guild):
        embed = discord.Embed(title="⚙️ Dem Feature Control", description="Toggle core modules for this server.", color=DEM_COLOR)
        
        features = ["antinuke", "security", "leveling", "booster", "welcome", "tickets"]
        status_text = ""
        for f in features:
            is_on = await self.get_state(guild.id, f)
            status_text += f"{'🟢' if is_on else '🔴'} **{f.capitalize()}**\n"
        
        embed.add_field(name="Current Status", value=status_text)
        return embed

    # =========================
    # HYBRID COMMANDS
    # =========================
    @commands.hybrid_command(name="setup", description="Open the feature control panel.")
    @commands.has_permissions(administrator=True)
    async def setup_panel(self, ctx):
        embed = await self.get_status_embed(ctx.guild)
        await ctx.send(embed=embed, view=ManagerPanel(self, ctx.guild.id))

    @commands.hybrid_command(name="activate", description="Enable a specific feature.")
    @app_commands.choices(feature=TOGGLE_CHOICES)
    @commands.has_permissions(administrator=True)
    async def activate(self, ctx, feature: app_commands.Choice[str]):
        await self.set_state(ctx.guild.id, feature.value, True)
        await ctx.send(f"✅ **{feature.name}** has been activated.")

    @commands.hybrid_command(name="deactivate", description="Disable a specific feature.")
    @app_commands.choices(feature=TOGGLE_CHOICES)
    @commands.has_permissions(administrator=True)
    async def deactivate(self, ctx, feature: app_commands.Choice[str]):
        await self.set_state(ctx.guild.id, feature.value, False)
        await ctx.send(f"❌ **{feature.name}** has been deactivated.")

async def setup(bot):
    await bot.add_cog(Manager(bot))
      
