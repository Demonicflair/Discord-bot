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
        messages.append(f"{msg.author}: {msg.content}")

    content = "\n".join(messages)
    return discord.File(io.BytesIO(content.encode()), filename=f"{channel.name}.txt")

# =========================
# DROPDOWN
# =========================
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support"),
            discord.SelectOption(label="Report"),
            discord.SelectOption(label="Other"),
        ]
        super().__init__(placeholder="Choose ticket type...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        # BLACKLIST
        cursor.execute("SELECT * FROM ticket_blacklist WHERE guild_id=? AND user_id=?", (guild.id, user.id))
        if cursor.fetchone():
            return await interaction.followup.send("❌ You are blacklisted", ephemeral=True)

        # COOLDOWN
        now = time.time()
        if user.id in user_cooldowns:
            if now - user_cooldowns[user.id] < COOLDOWN:
                return await interaction.followup.send("⏳ Wait before creating another ticket", ephemeral=True)

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY)

        count = sum(1 for ch in category.channels if str(user.id) in ch.name)
        if count >= TICKET_LIMIT:
            return await interaction.followup.send("❌ Ticket limit reached", ephemeral=True)

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

        channel = await guild.create_text_channel(
            name=f"{self.values[0].lower()}-{user.id}",
            category=category,
            overwrites=overwrites
        )

        user_cooldowns[user.id] = now

        await channel.send(
            content=mention_text,
            embed=discord.Embed(
                title=f"{self.values[0]} Ticket",
                description="Support will assist you.",
                color=discord.Color.green()
            ),
            view=TicketControlView()
        )

        await interaction.followup.send(f"✅ {channel.mention}", ephemeral=True)

        # LOG CREATE
        await send_log(guild, "ticket", f"🎫 Ticket created: {channel.name} by {user}")

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

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple)
    async def claim(self, interaction: discord.Interaction, button):
        await interaction.response.send_message(f"🛠️ Claimed by {interaction.user.mention}")

        await send_log(interaction.guild, "ticket", f"🛠️ {interaction.user} claimed {interaction.channel.name}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button):

        await interaction.response.defer()

        guild = interaction.guild
        channel = interaction.channel

        file = await create_transcript(channel)

        await send_log(
            guild,
            "ticket",
            f"📁 Closed: {channel.name}",
            file=file
        )

        await channel.send("🔒 Closing in 3s...")
        await asyncio.sleep(3)

        try:
            await channel.delete()
        except:
            pass

# =========================
# COG
# =========================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="assign")
    async def assign(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.channel.set_permissions(user, send_messages=True, read_messages=True)
        await interaction.response.send_message(f"👤 Assigned {user.mention}")

        await send_log(interaction.guild, "ticket", f"👤 {user} assigned to {interaction.channel.name}")

    @app_commands.command(name="unassign")
    async def unassign(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"❌ Unassigned {user.mention}")

        await send_log(interaction.guild, "ticket", f"❌ {user} unassigned from {interaction.channel.name}")

    @app_commands.command(name="blacklist")
    async def blacklist(self, interaction: discord.Interaction, user: discord.Member):
        cursor.execute("INSERT INTO ticket_blacklist VALUES (?, ?)", (interaction.guild.id, user.id))
        db.commit()

        await interaction.response.send_message(f"🚫 Blacklisted {user.mention}")
        await send_log(interaction.guild, "ticket", f"🚫 {user} blacklisted")

    @app_commands.command(name="unblacklist")
    async def unblacklist(self, interaction: discord.Interaction, user: discord.Member):
        cursor.execute("DELETE FROM ticket_blacklist WHERE guild_id=? AND user_id=?", (interaction.guild.id, user.id))
        db.commit()

        await interaction.response.send_message(f"✅ Unblacklisted {user.mention}")
        await send_log(interaction.guild, "ticket", f"✅ {user} unblacklisted")

    @app_commands.command(name="ticketpanel")
    async def ticketpanel(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="🎫 Tickets", description="Choose below"),
            view=TicketView()
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
