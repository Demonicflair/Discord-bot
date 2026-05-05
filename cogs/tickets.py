import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import sqlite3
import io

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

db.commit()


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
            discord.SelectOption(label="Support", description="General help"),
            discord.SelectOption(label="Report", description="Report a user"),
            discord.SelectOption(label="Other", description="Other issues"),
        ]
        super().__init__(placeholder="Choose ticket type...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY)

        for ch in category.channels:
            if ch.name.endswith(str(user.id)):
                return await interaction.followup.send("❌ You already have a ticket!", ephemeral=True)

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

        await channel.send(
            content=mention_text,
            embed=discord.Embed(
                title=f"{self.values[0]} Ticket",
                description="Support will assist you.",
                color=discord.Color.green()
            ),
            view=TicketControlView()
        )

        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


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
                    f"📁 Ticket Closed: {interaction.channel.name}",
                    file=file
                )

        await interaction.channel.send("🔒 Ticket closed. Deleting in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()


# =========================
# 🎫 COG
# =========================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ SET LOG CHANNEL
    @app_commands.command(name="setlog", description="Set ticket log channel")
    async def setlog(self, interaction: discord.Interaction, channel: discord.TextChannel):

        cursor.execute("DELETE FROM ticket_logs WHERE guild_id=?", (interaction.guild.id,))
        cursor.execute("INSERT INTO ticket_logs VALUES (?, ?)", (interaction.guild.id, channel.id))
        db.commit()

        await interaction.response.send_message(f"✅ Log channel set to {channel.mention}")

    # ➕ ADD SUPPORT ROLE
    @app_commands.command(name="addsupport", description="Add support role")
    async def addsupport(self, interaction: discord.Interaction, role: discord.Role):

        cursor.execute("INSERT INTO ticket_settings VALUES (?, ?)", (interaction.guild.id, role.id))
        db.commit()

        await interaction.response.send_message(f"✅ Added {role.mention}")

    @commands.command()
    async def addsupport(self, ctx, role: discord.Role):
        cursor.execute("INSERT INTO ticket_settings VALUES (?, ?)", (ctx.guild.id, role.id))
        db.commit()
        await ctx.send(f"✅ Added {role.mention}")

    # ❌ REMOVE SUPPORT ROLE (NEW)
    @app_commands.command(name="removesupport", description="Remove support role")
    async def removesupport(self, interaction: discord.Interaction, role: discord.Role):

        cursor.execute(
            "DELETE FROM ticket_settings WHERE guild_id=? AND role_id=?",
            (interaction.guild.id, role.id)
        )
        db.commit()

        await interaction.response.send_message(f"❌ Removed {role.mention}")

    @commands.command()
    async def removesupport(self, ctx, role: discord.Role):
        cursor.execute(
            "DELETE FROM ticket_settings WHERE guild_id=? AND role_id=?",
            (ctx.guild.id, role.id)
        )
        db.commit()
        await ctx.send(f"❌ Removed {role.mention}")

    # 🎫 PANEL
    @app_commands.command(name="ticketpanel", description="Send panel")
    async def ticketpanel(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🎫 Support System",
            description="Select a category below to open a ticket",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed, view=TicketView())

    @commands.command()
    async def panel(self, ctx):
        embed = discord.Embed(
            title="🎫 Support System",
            description="Select a category below",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed, view=TicketView())


async def setup(bot):
    await bot.add_cog(Tickets(bot))
