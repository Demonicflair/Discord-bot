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
# 📜 TRANSCRIPT
# =========================
async def create_transcript(channel):
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        messages.append(f"{msg.author}: {msg.content}")

    content = "\n".join(messages)

    return discord.File(
        fp=bytes(content, "utf-8"),
        filename=f"{channel.name}.txt"
    )


# =========================
# 🎫 OPEN BUTTON
# =========================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY)

        for ch in category.channels:
            if ch.name == f"ticket-{user.id}":
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
            name=f"ticket-{user.id}",
            category=category,
            overwrites=overwrites
        )

        await channel.send(
            content=mention_text,
            embed=discord.Embed(
                title="🎫 Ticket Opened",
                description="Support will assist you shortly.",
                color=discord.Color.green()
            ),
            view=TicketControlView()
        )

        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


# =========================
# 🔒 CONTROL
# =========================
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.blurple)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🛠️ Claimed by {interaction.user.mention}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message("📜 Saving transcript...")

        file = await create_transcript(interaction.channel)
        await interaction.channel.send(file=file)

        await asyncio.sleep(3)
        await interaction.channel.delete()


# =========================
# 🎫 MAIN COG
# =========================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ----------------------
    # ➕ ADD SUPPORT ROLE
    # ----------------------
    @app_commands.command(name="addsupport", description="Add support role")
    async def addsupport_slash(self, interaction: discord.Interaction, role: discord.Role):

        cursor.execute("INSERT INTO ticket_settings VALUES (?, ?)", (interaction.guild.id, role.id))
        db.commit()

        await interaction.response.send_message(f"✅ Added {role.mention}")

    @commands.command()
    async def addsupport(self, ctx, role: discord.Role):
        cursor.execute("INSERT INTO ticket_settings VALUES (?, ?)", (ctx.guild.id, role.id))
        db.commit()
        await ctx.send(f"✅ Added {role.mention}")

    # ----------------------
    # ➖ REMOVE SUPPORT ROLE
    # ----------------------
    @app_commands.command(name="removesupport", description="Remove support role")
    async def removesupport_slash(self, interaction: discord.Interaction, role: discord.Role):

        cursor.execute("DELETE FROM ticket_settings WHERE guild_id=? AND role_id=?", (interaction.guild.id, role.id))
        db.commit()

        await interaction.response.send_message(f"❌ Removed {role.mention}")

    @commands.command()
    async def removesupport(self, ctx, role: discord.Role):
        cursor.execute("DELETE FROM ticket_settings WHERE guild_id=? AND role_id=?", (ctx.guild.id, role.id))
        db.commit()
        await ctx.send(f"❌ Removed {role.mention}")

    # ----------------------
    # 📋 LIST SUPPORT ROLES
    # ----------------------
    @app_commands.command(name="listsupport", description="List support roles")
    async def listsupport_slash(self, interaction: discord.Interaction):

        cursor.execute("SELECT role_id FROM ticket_settings WHERE guild_id=?", (interaction.guild.id,))
        roles = cursor.fetchall()

        if not roles:
            return await interaction.response.send_message("No support roles set")

        text = ""
        for r in roles:
            role = interaction.guild.get_role(r[0])
            if role:
                text += f"{role.mention}\n"

        await interaction.response.send_message(text)

    @commands.command()
    async def listsupport(self, ctx):

        cursor.execute("SELECT role_id FROM ticket_settings WHERE guild_id=?", (ctx.guild.id,))
        roles = cursor.fetchall()

        if not roles:
            return await ctx.send("No support roles set")

        text = ""
        for r in roles:
            role = ctx.guild.get_role(r[0])
            if role:
                text += f"{role.mention}\n"

        await ctx.send(text)

    # ----------------------
    # 🧹 CLEAR ALL ROLES
    # ----------------------
    @app_commands.command(name="clearsupport", description="Clear all support roles")
    async def clearsupport_slash(self, interaction: discord.Interaction):

        cursor.execute("DELETE FROM ticket_settings WHERE guild_id=?", (interaction.guild.id,))
        db.commit()

        await interaction.response.send_message("🧹 Cleared all support roles")

    @commands.command()
    async def clearsupport(self, ctx):
        cursor.execute("DELETE FROM ticket_settings WHERE guild_id=?", (ctx.guild.id,))
        db.commit()
        await ctx.send("🧹 Cleared all support roles")

    # ----------------------
    # 🎫 PANEL
    # ----------------------
    @app_commands.command(name="ticketpanel", description="Send ticket panel")
    async def ticketpanel(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🎫 Support System",
            description="Click below to open a ticket",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed, view=TicketView())

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
