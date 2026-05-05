import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import sqlite3
import io
import time

TICKET_CATEGORY = "Tickets"

# =========================
# 💾 DATABASE
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
CREATE TABLE IF NOT EXISTS ticket_logs(
    guild_id INTEGER,
    channel_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ticket_blacklist(
    guild_id INTEGER,
    user_id INTEGER
)
""")

db.commit()

# =========================
# ⚙️ CONFIG
# =========================
TICKET_LIMIT = 1
COOLDOWN = 30

user_cooldowns = {}

# =========================
# 📜 TRANSCRIPT
# =========================
async def create_transcript(channel):
    messages = []
    async for msg in channel.history(limit=1000, oldest_first=True):
        messages.append(f"{msg.author}: {msg.content}")

    content = "\n".join(messages)
    return discord.File(io.BytesIO(content.encode()), filename=f"{channel.name}.txt")


# =========================
# 🎯 DROPDOWN
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

        # 🚫 BLACKLIST CHECK
        cursor.execute("SELECT * FROM ticket_blacklist WHERE guild_id=? AND user_id=?", (guild.id, user.id))
        if cursor.fetchone():
            return await interaction.followup.send("❌ You are blacklisted from tickets", ephemeral=True)

        # ⏱️ COOLDOWN
        now = time.time()
        if user.id in user_cooldowns:
            if now - user_cooldowns[user.id] < COOLDOWN:
                return await interaction.followup.send(
                    f"⏳ Wait {int(COOLDOWN - (now - user_cooldowns[user.id]))}s",
                    ephemeral=True
                )

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY)

        # 📊 LIMIT
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


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


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

        await interaction.response.defer()

        guild = interaction.guild
        file = await create_transcript(interaction.channel)

        cursor.execute("SELECT channel_id FROM ticket_logs WHERE guild_id=?", (guild.id,))
        data = cursor.fetchone()

        if data:
            log_channel = guild.get_channel(data[0])
            if log_channel:
                await log_channel.send(
                    f"📁 Closed: {interaction.channel.name}",
                    file=file
                )

        await interaction.channel.send("🔒 Closing in 3s...")
        await asyncio.sleep(3)
        await interaction.channel.delete()


# =========================
# 🎫 COG
# =========================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_permission(self, interaction):
        return interaction.user.guild_permissions.manage_guild

    # 👤 ASSIGN
    @app_commands.command(name="assign")
    async def assign(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.channel.set_permissions(user, send_messages=True, read_messages=True)
        await interaction.response.send_message(f"👤 Assigned {user.mention}")

    @app_commands.command(name="unassign")
    async def unassign(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"❌ Unassigned {user.mention}")

    # 🚫 BLACKLIST
    @app_commands.command(name="blacklist")
    async def blacklist(self, interaction: discord.Interaction, user: discord.Member):
        cursor.execute("INSERT INTO ticket_blacklist VALUES (?, ?)", (interaction.guild.id, user.id))
        db.commit()
        await interaction.response.send_message(f"🚫 Blacklisted {user.mention}")

    @app_commands.command(name="unblacklist")
    async def unblacklist(self, interaction: discord.Interaction, user: discord.Member):
        cursor.execute("DELETE FROM ticket_blacklist WHERE guild_id=? AND user_id=?", (interaction.guild.id, user.id))
        db.commit()
        await interaction.response.send_message(f"✅ Unblacklisted {user.mention}")

    # 🎫 PANEL
    @app_commands.command(name="ticketpanel")
    async def ticketpanel(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(title="🎫 Tickets", description="Choose below"),
            view=TicketView()
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
