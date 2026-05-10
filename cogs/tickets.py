import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio
from utils.dispatch import dispatch_log

DB_PATH = "data.db"

# =========================
# 🔘 PERSISTENT BUTTONS
# =========================
class TicketView(discord.ui.View):
    """The permanent button that sits in your #support channel."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Support Ticket", style=discord.ButtonStyle.blurple, custom_id="dem_ticket_open", emoji="📩")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Create a private thread or channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=interaction.channel.category, # Opens in the same category
            overwrites=overwrites,
            reason=f"Ticket opened by {user}"
        )

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Welcome {user.mention}, staff will be with you shortly.\nUse the button below to close this ticket.",
            color=0x2b2d31
        )
        await channel.send(embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class TicketControlView(discord.ui.View):
    """The buttons inside the ticket channel itself."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="dem_ticket_close", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# =========================
# ⚙️ TICKET COG
# =========================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="ticket", description="🎫 Manage the Ticket System.")
    @commands.has_permissions(administrator=True)
    async def ticket(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @ticket.command(name="setup", description="🚀 Send the Ticket creation message to this channel.")
    async def setup(self, ctx):
        embed = discord.Embed(
            title="📩 Need Assistance?",
            description="Click the button below to open a private support ticket with the staff team.",
            color=0x2b2d31
        )
        embed.set_footer(text="Dem Support System")
        await ctx.send(embed=embed, view=TicketView())

    @ticket.command(name="blacklist", description="🚫 Block a user from creating tickets.")
    @app_commands.describe(user="The user to blacklist")
    async def blacklist(self, ctx, user: discord.Member):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO ticket_blacklist VALUES (?, ?)", (ctx.guild.id, user.id))
            await db.commit()
        await ctx.send(f"🚫 {user.mention} is now blacklisted from the ticket system.")

async def setup(bot):
    await bot.add_cog(Tickets(bot))
    
