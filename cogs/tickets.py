import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiosqlite
import io
import time
import datetime
from utils.logger import get_logs, save_log, is_log_enabled

# Configuration
TICKET_CATEGORY_NAME = "Tickets"
DB_PATH = "bot.db"
BRAND_COLOR = 0x2b2d31 

# =========================
# TRANSCRIPT SYSTEM
# =========================
async def create_transcript(channel: discord.TextChannel):
    """Generates a professional transcript of the ticket."""
    messages = []
    async for msg in channel.history(limit=1000, oldest_first=True):
        timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M')
        messages.append(f"[{timestamp}] {msg.author}: {msg.clean_content}")

    content = "\n".join(messages)
    return discord.File(
        io.BytesIO(content.encode()),
        filename=f"transcript-{channel.name}.txt"
    )

# =========================
# PERSISTENT BUTTONS
# =========================
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple, emoji="🛠️", custom_id="persistent:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Only staff can claim tickets.", ephemeral=True)
        
        button.disabled = True
        button.label = f"Claimed by {interaction.user.name}"
        button.style = discord.ButtonStyle.gray
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"🛠️ Ticket claimed by {interaction.user.mention}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒", custom_id="persistent:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Create transcript & Log
        file = await create_transcript(interaction.channel)
        logs = get_logs(interaction.guild.id)
        if logs and is_log_enabled(interaction.guild.id, "ticket"):
            log_channel = interaction.guild.get_channel(logs[1])
            if log_channel:
                await log_channel.send(f"📁 Closed ticket: `{interaction.channel.name}`", file=file)

        await interaction.channel.send("🔒 Closing in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# =========================
# DROPDOWN SELECT
# =========================
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support", emoji="🛠️", description="General support", value="support"),
            discord.SelectOption(label="Report", emoji="🚨", description="Report an issue", value="report"),
            discord.SelectOption(label="Other", emoji="📦", description="Other questions", value="other")
        ]
        super().__init__(placeholder="Choose ticket type...", options=options, custom_id="persistent:dropdown")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Blacklist Check
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM ticket_blacklist WHERE guild_id=? AND user_id=?", (guild.id, user.id)) as cur:
                if await cur.fetchone():
                    return await interaction.response.send_message("❌ You are blacklisted.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # Create Category
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        # Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"{self.values[0]}-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"🎫 {self.values[0].title()} Ticket",
            description="Staff will assist you shortly.\nUse the buttons below to manage this ticket.",
            color=discord.Color.green()
        )
        await channel.send(content=f"{user.mention} | Support Team", embed=embed, view=TicketControlView())
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# =========================
# HYBRID COG
# =========================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS ticket_blacklist (guild_id INTEGER, user_id INTEGER, PRIMARY KEY(guild_id, user_id))")
            await db.commit()

    @commands.hybrid_command(name="ticketpanel", description="📢 Send the ticket creation panel.")
    @commands.has_permissions(manage_guild=True)
    async def ticketpanel(self, ctx):
        embed = discord.Embed(title="🎫 Support Tickets", description="Select a category to open a ticket.", color=BRAND_COLOR)
        await ctx.send(embed=embed, view=TicketView())

    @commands.hybrid_command(name="assign", description="👤 Add a user to the ticket.")
    @commands.has_permissions(manage_channels=True)
    async def assign(self, ctx, user: discord.Member):
        await ctx.channel.set_permissions(user, read_messages=True, send_messages=True)
        await ctx.send(f"✅ Assigned {user.mention}")

    @commands.hybrid_command(name="t-blacklist", description="🚫 Blacklist a user from tickets.")
    @commands.has_permissions(manage_guild=True)
    async def blacklist(self, ctx, user: discord.Member):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO ticket_blacklist VALUES (?, ?)", (ctx.guild.id, user.id))
            await db.commit()
        await ctx.send(f"🚫 {user.mention} blacklisted.")

async def setup(bot):
    await bot.add_cog(Tickets(bot))
