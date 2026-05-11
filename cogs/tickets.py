import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio

from utils.dispatch import dispatch_log
from utils.config import STAFF_ROLE_NAME

DB_PATH = "data.db"

# =========================
# HELPER FUNCTIONS
# =========================

async def user_has_open_ticket(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT channel_id
            FROM tickets
            WHERE guild_id=? AND user_id=? AND closed=0
            """,
            (guild_id, user_id)
        ) as cursor:

            return await cursor.fetchone()


async def is_blacklisted(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT *
            FROM ticket_blacklist
            WHERE guild_id=? AND user_id=?
            """,
            (guild_id, user_id)
        ) as cursor:

            return await cursor.fetchone()


# =========================
# OPEN TICKET VIEW
# =========================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open Support Ticket",
        style=discord.ButtonStyle.blurple,
        emoji="📩",
        custom_id="dem_ticket_open"
    )
    async def open_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild
        user = interaction.user

        # =========================
        # BLACKLIST CHECK
        # =========================

        blacklisted = await is_blacklisted(
            guild.id,
            user.id
        )

        if blacklisted:
            return await interaction.response.send_message(
                "❌ You are blacklisted from the ticket system.",
                ephemeral=True
            )

        # =========================
        # DUPLICATE CHECK
        # =========================

        existing = await user_has_open_ticket(
            guild.id,
            user.id
        )

        if existing:
            channel = guild.get_channel(existing[0])

            if channel:
                return await interaction.response.send_message(
                    f"❌ You already have an open ticket: {channel.mention}",
                    ephemeral=True
                )

        # =========================
        # STAFF ROLE
        # =========================

        staff_role = discord.utils.get(
            guild.roles,
            name=STAFF_ROLE_NAME
        )

        # =========================
        # OVERWRITES
        # =========================

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True
            ),

            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        # =========================
        # CATEGORY
        # =========================

        category = interaction.channel.category

        # =========================
        # CREATE CHANNEL
        # =========================

        safe_name = user.name.lower().replace(" ", "-")

        channel = await guild.create_text_channel(
            name=f"ticket-{safe_name}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket opened by {user}"
        )

        # =========================
        # SAVE TICKET
        # =========================

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT INTO tickets
                (guild_id, user_id, channel_id, closed)
                VALUES (?, ?, ?, 0)
                """,
                (
                    guild.id,
                    user.id,
                    channel.id
                )
            )

            await db.commit()

        # =========================
        # EMBED
        # =========================

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Welcome {user.mention}\n\n"
                "Please explain your issue clearly.\n"
                "A staff member will help you soon."
            ),
            color=0x2b2d31
        )

        embed.set_footer(
            text="Dem Support System"
        )

        await channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=TicketControlView()
        )

        # =========================
        # RESPONSE
        # =========================

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

        # =========================
        # LOGGING
        # =========================

        await dispatch_log(
            guild,
            "ticket_create",
            (
                f"🎫 Ticket Created\n"
                f"User: {user} ({user.id})\n"
                f"Channel: {channel.mention}"
            ),
            user_id=user.id
        )


# =========================
# CONTROL VIEW
# =========================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="dem_ticket_close"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.channel

        await interaction.response.send_message(
            "🔒 Closing ticket in 5 seconds..."
        )

        # =========================
        # MARK CLOSED
        # =========================

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                UPDATE tickets
                SET closed=1
                WHERE channel_id=?
                """,
                (channel.id,)
            )

            await db.commit()

        # =========================
        # LOG
        # =========================

        await dispatch_log(
            interaction.guild,
            "ticket_close",
            f"🔒 Ticket Closed: {channel.name}"
        )

        await asyncio.sleep(5)

        try:
            await channel.delete()

        except Exception as e:
            print(f"[TICKET DELETE ERROR] {e}")


# =========================
# TICKET COG
# =========================

class Tickets(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # =========================
    # GROUP
    # =========================

    @commands.hybrid_group(
        name="ticket",
        description="🎫 Ticket system commands."
    )
    @commands.has_permissions(administrator=True)
    async def ticket(self, ctx):

        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    # =========================
    # SETUP
    # =========================

    @ticket.command(
        name="setup",
        description="Setup ticket panel."
    )
    async def setup_ticket(self, ctx):

        embed = discord.Embed(
            title="📩 Need Help?",
            description=(
                "Click the button below "
                "to open a support ticket."
            ),
            color=0x2b2d31
        )

        embed.set_footer(
            text="Dem Ticket System"
        )

        await ctx.send(
            embed=embed,
            view=TicketView()
        )

    # =========================
    # BLACKLIST
    # =========================

    @ticket.command(
        name="blacklist",
        description="Blacklist a user from tickets."
    )
    @app_commands.describe(
        user="User to blacklist"
    )
    async def blacklist(
        self,
        ctx,
        user: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT OR REPLACE INTO ticket_blacklist
                VALUES (?, ?)
                """,
                (
                    ctx.guild.id,
                    user.id
                )
            )

            await db.commit()

        await ctx.send(
            f"🚫 {user.mention} "
            "has been blacklisted from tickets."
        )

    # =========================
    # UNBLACKLIST
    # =========================

    @ticket.command(
        name="unblacklist",
        description="Remove ticket blacklist."
    )
    async def unblacklist(
        self,
        ctx,
        user: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                DELETE FROM ticket_blacklist
                WHERE guild_id=? AND user_id=?
                """,
                (
                    ctx.guild.id,
                    user.id
                )
            )

            await db.commit()

        await ctx.send(
            f"✅ {user.mention} "
            "can use tickets again."
        )


# =========================
# LOAD COG
# =========================

async def setup(bot):
    await bot.add_cog(Tickets(bot))
