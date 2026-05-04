import discord
from discord.ext import commands
from discord import app_commands

TICKET_CATEGORY = "Tickets"
STAFF_ROLE_NAME = "Staff"

# =========================
# 🎫 BUTTON VIEW
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = interaction.user

        # Get or create category
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY)

        # Check if ticket already exists
        for ch in category.channels:
            if ch.name == f"ticket-{user.id}":
                return await interaction.response.send_message(
                    "❌ You already have a ticket open!",
                    ephemeral=True
                )

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Ticket Created",
            description="A staff member will assist you shortly.",
            color=discord.Color.green()
        )

        await channel.send(
            content=f"{user.mention} {staff_role.mention}",
            embed=embed,
            view=CloseView()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )


# =========================
# 🔒 CLOSE VIEW
# =========================
class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"🛠️ Ticket claimed by {interaction.user.mention}"
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
        await interaction.channel.delete()


# =========================
# 🎫 TICKET COG
# =========================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # SLASH COMMAND
    @app_commands.command(name="ticketpanel", description="Send ticket panel")
    async def ticketpanel(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🎫 Support System",
            description="Click below to open a ticket",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=TicketView()
        )

    # PREFIX COMMAND
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
