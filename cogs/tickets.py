import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import sqlite3

TICKET_CATEGORY = "Tickets"

# =========================
# 💾 DATABASE
# =========================
db = sqlite3.connect("tickets.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS ticket_settings(
    guild_id INTEGER,
    role_id INTEGER
)
""")
db.commit()

# =========================
# 🎫 OPEN BUTTON VIEW
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        # Get/Create category
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY)

        # Prevent duplicate tickets
        for ch in category.channels:
            if ch.name == f"ticket-{user.id}":
                return await interaction.followup.send("❌ You already have a ticket open!", ephemeral=True)

        # Get support roles
        cursor.execute("SELECT role_id FROM ticket_settings WHERE guild_id=?", (guild.id,))
        roles = cursor.fetchall()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        mention_text = user.mention

        for r in roles:
            role = guild.get_role(r[0])
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                mention_text += f" {role.mention}"

        # Create channel
        channel = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Ticket Opened",
            description="Support will be with you shortly.",
            color=discord.Color.green()
        )

        await channel.send(
            content=mention_text,
            embed=embed,
            view=TicketControlView()
        )

        await interaction.followup.send(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

# =========================
# 🔒 CONTROL VIEW
# =========================
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🛠️ Claimed by {interaction.user.mention}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# =========================
# 🎫 MAIN COG
# =========================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🎛️ ADD SUPPORT ROLE (SLASH)
    @app_commands.command(name="addsupport", description="Add a role to be pinged in tickets")
    async def addsupport(self, interaction: discord.Interaction, role: discord.Role):

        cursor.execute("INSERT INTO ticket_settings VALUES (?, ?)", (interaction.guild.id, role.id))
        db.commit()

        await interaction.response.send_message(f"✅ {role.mention} will now be pinged in tickets")

    # 🎛️ REMOVE SUPPORT ROLE
    @app_commands.command(name="removesupport", description="Remove a support role")
    async def removesupport(self, interaction: discord.Interaction, role: discord.Role):

        cursor.execute("DELETE FROM ticket_settings WHERE guild_id=? AND role_id=?", (interaction.guild.id, role.id))
        db.commit()

        await interaction.response.send_message(f"❌ Removed {role.mention} from ticket support roles")

    # 🎫 PANEL (SLASH)
    @app_commands.command(name="ticketpanel", description="Send ticket panel")
    async def ticketpanel(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🎫 Support System",
            description="Click below to open a ticket",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed, view=TicketView())

    # 🎫 PANEL (PREFIX)
    @commands.command()
    async def panel(self, ctx):
        embed = discord.Embed(
            title="🎫 Support System",
            description="Click below to open a ticket",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed, view=TicketView())


async def setup(bot):
    await bot.add_cog(Tickets(bot))
