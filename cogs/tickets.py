import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import sqlite3
import io
import time

from utils.logger import get_logs, save_log, is_log_enabled

TICKET_CATEGORY = "Tickets"

# =========================
# DATABASE
# =========================
db = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS ticket_settings(
    guild_id INTEGER,
    role_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ticket_blacklist(
    guild_id INTEGER,
    user_id INTEGER
)
""")

db.commit()

TICKET_LIMIT = 1
COOLDOWN = 30

user_cooldowns = {}

# =========================
# LOG SYSTEM
# =========================
async def send_log(guild, log_type, content, file=None):

    logs = get_logs(guild.id)

    if logs and is_log_enabled(guild.id, log_type):

        channel = guild.get_channel(logs[1])

        if channel:

            if file:
                await channel.send(content=content, file=file)

            else:
                await channel.send(content)

    save_log(guild.id, 0, log_type, content)

# =========================
# TRANSCRIPT
# =========================
async def create_transcript(channel):

    messages = []

    async for msg in channel.history(limit=1000, oldest_first=True):

        messages.append(
            f"[{msg.created_at.strftime('%Y-%m-%d %H:%M')}] "
            f"{msg.author}: {msg.content}"
        )

    content = "\n".join(messages)

    return discord.File(
        io.BytesIO(content.encode()),
        filename=f"{channel.name}.txt"
    )

# =========================
# DROPDOWN
# =========================
class TicketDropdown(discord.ui.Select):

    def __init__(self):

        options = [
            discord.SelectOption(
                label="Support",
                emoji="🛠️",
                description="General support ticket"
            ),

            discord.SelectOption(
                label="Report",
                emoji="🚨",
                description="Report a user or issue"
            ),

            discord.SelectOption(
                label="Other",
                emoji="📦",
                description="Other questions"
            )
        ]

        super().__init__(
            placeholder="Choose ticket type...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        # =========================
        # BLACKLIST CHECK
        # =========================
        cursor.execute(
            "SELECT * FROM ticket_blacklist WHERE guild_id=? AND user_id=?",
            (guild.id, user.id)
        )

        if cursor.fetchone():

            return await interaction.followup.send(
                "❌ You are blacklisted from tickets",
                ephemeral=True
            )

        # =========================
        # COOLDOWN
        # =========================
        now = time.time()

        if user.id in user_cooldowns:

            remaining = COOLDOWN - (now - user_cooldowns[user.id])

            if remaining > 0:

                return await interaction.followup.send(
                    f"⏳ Wait `{int(remaining)}s` before creating another ticket",
                    ephemeral=True
                )

        # =========================
        # CATEGORY
        # =========================
        category = discord.utils.get(
            guild.categories,
            name=TICKET_CATEGORY
        )

        if category is None:

            category = await guild.create_category(
                TICKET_CATEGORY
            )

        # =========================
        # LIMIT
        # =========================
        count = sum(
            1 for ch in category.channels
            if str(user.id) in ch.name
        )

        if count >= TICKET_LIMIT:

            return await interaction.followup.send(
                "❌ Ticket limit reached",
                ephemeral=True
            )

        # =========================
        # SUPPORT ROLES
        # =========================
        cursor.execute(
            "SELECT role_id FROM ticket_settings WHERE guild_id=?",
            (guild.id,)
        )

        roles = cursor.fetchall()

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    read_messages=False
                ),

            user:
                discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True
                )
        }

        mention_text = user.mention

        for r in roles:

            role = guild.get_role(r[0])

            if role:

                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )

                mention_text += f" {role.mention}"

        # =========================
        # CREATE CHANNEL
        # =========================
        channel = await guild.create_text_channel(
            name=f"{self.values[0].lower()}-{user.id}",
            category=category,
            overwrites=overwrites
        )

        user_cooldowns[user.id] = now

        embed = discord.Embed(
            title=f"🎫 {self.values[0]} Ticket",
            description=(
                "Support will assist you shortly.\n\n"
                "Use the buttons below to manage this ticket."
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text=f"Opened by {user}",
            icon_url=user.display_avatar.url
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
        # LOG
        # =========================
        await send_log(
            guild,
            "ticket",
            f"🎫 Ticket created: {channel.name} by {user}"
        )

# =========================
# MAIN VIEW
# =========================
class TicketView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(TicketDropdown())

# =========================
# CONTROL VIEW
# =========================
class TicketControlView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    # =========================
    # CLAIM
    # =========================
    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.blurple,
        emoji="🛠️"
    )
    async def claim(self, interaction: discord.Interaction, button):

        await interaction.response.send_message(
            f"🛠️ Claimed by {interaction.user.mention}"
        )

        await send_log(
            interaction.guild,
            "ticket",
            f"🛠️ {interaction.user} claimed {interaction.channel.name}"
        )

    # =========================
    # CLOSE
    # =========================
    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        emoji="🔒"
    )
    async def close(self, interaction: discord.Interaction, button):

        await interaction.response.defer()

        guild = interaction.guild
        channel = interaction.channel

        file = await create_transcript(channel)

        await send_log(
            guild,
            "ticket",
            f"📁 Closed ticket: {channel.name}",
            file=file
        )

        await channel.send("🔒 Closing ticket in 3 seconds...")

        await asyncio.sleep(3)

        try:
            await channel.delete()

        except:
            pass

# =========================
# TICKETS COG
# =========================
class Tickets(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # ASSIGN
    # =========================
    @commands.hybrid_command(
        name="assign",
        help="Assign a user to the current ticket.",
        extras={
            "example": "!assign @user",
            "tips": "Assigned users can view and respond inside the ticket."
        }
    )
    @commands.has_permissions(manage_channels=True)
    async def assign(self, ctx, user: discord.Member):
        """Assign a user to the current ticket."""

        await ctx.channel.set_permissions(
            user,
            send_messages=True,
            read_messages=True
        )

        await ctx.send(f"👤 Assigned {user.mention}")

        await send_log(
            ctx.guild,
            "ticket",
            f"👤 {user} assigned to {ctx.channel.name}"
        )

    # =========================
    # UNASSIGN
    # =========================
    @commands.hybrid_command(
        name="unassign",
        help="Remove a user from the current ticket.",
        extras={
            "example": "!unassign @user",
            "tips": "This removes their access to the ticket."
        }
    )
    @commands.has_permissions(manage_channels=True)
    async def unassign(self, ctx, user: discord.Member):
        """Remove a user from the current ticket."""

        await ctx.channel.set_permissions(
            user,
            overwrite=None
        )

        await ctx.send(f"❌ Unassigned {user.mention}")

        await send_log(
            ctx.guild,
            "ticket",
            f"❌ {user} unassigned from {ctx.channel.name}"
        )

    # =========================
    # BLACKLIST
    # =========================
    @commands.hybrid_command(
        name="blacklist",
        help="Blacklist a user from creating tickets.",
        extras={
            "example": "!blacklist @user",
            "tips": "Use this against ticket abusers."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def blacklist(self, ctx, user: discord.Member):
        """Blacklist a user from tickets."""

        cursor.execute(
            "INSERT INTO ticket_blacklist VALUES (?, ?)",
            (ctx.guild.id, user.id)
        )

        db.commit()

        await ctx.send(f"🚫 Blacklisted {user.mention}")

        await send_log(
            ctx.guild,
            "ticket",
            f"🚫 {user} blacklisted from tickets"
        )

    # =========================
    # UNBLACKLIST
    # =========================
    @commands.hybrid_command(
        name="unblacklist",
        help="Remove a user from the ticket blacklist.",
        extras={
            "example": "!unblacklist @user",
            "tips": "Allows the user to create tickets again."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def unblacklist(self, ctx, user: discord.Member):
        """Remove a user from the ticket blacklist."""

        cursor.execute(
            "DELETE FROM ticket_blacklist WHERE guild_id=? AND user_id=?",
            (ctx.guild.id, user.id)
        )

        db.commit()

        await ctx.send(f"✅ Unblacklisted {user.mention}")

        await send_log(
            ctx.guild,
            "ticket",
            f"✅ {user} removed from ticket blacklist"
        )

    # =========================
    # TICKET PANEL
    # =========================
    @commands.hybrid_command(
        name="ticketpanel",
        help="Send the ticket creation panel.",
        extras={
            "example": "!ticketpanel",
            "tips": "Users can create tickets using the dropdown."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def ticketpanel(self, ctx):
        """Send the ticket creation panel."""

        embed = discord.Embed(
            title="🎫 Support Tickets",
            description=(
                "Need help?\n\n"
                "Choose a ticket type from the dropdown below."
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text="Ticket System"
        )

        await ctx.send(
            embed=embed,
            view=TicketView()
        )

# =========================
# SETUP
# =========================
async def setup(bot):

    await bot.add_cog(Tickets(bot))
