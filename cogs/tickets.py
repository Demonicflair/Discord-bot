import io
import asyncio
import aiosqlite
import discord

from datetime import datetime
from discord.ext import commands
from discord import app_commands

from utils.dispatch import dispatch_log
from utils.config import STAFF_ROLE_NAME

DB_PATH = "data.db"

TICKET_COLOR = 0x2b2d31


# =========================
# HELPERS
# =========================

async def get_ticket_settings(guild_id: int):

    async with aiosqlite.connect(DB_PATH) as db:

        async with db.execute(
            """
            SELECT
            category_id,
            log_channel,
            panel_channel,
            support_role
            FROM ticket_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        ) as cursor:

            return await cursor.fetchone()


async def get_open_ticket(guild_id: int, user_id: int):

    async with aiosqlite.connect(DB_PATH) as db:

        async with db.execute(
            """
            SELECT channel_id
            FROM active_tickets
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id)
        ) as cursor:

            return await cursor.fetchone()


async def is_blacklisted(guild_id: int, user_id: int):

    async with aiosqlite.connect(DB_PATH) as db:

        async with db.execute(
            """
            SELECT *
            FROM ticket_blacklist
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id)
        ) as cursor:

            return await cursor.fetchone()


async def save_ticket(channel_id, guild_id, user_id):

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT OR REPLACE INTO active_tickets
            (
                channel_id,
                guild_id,
                user_id,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                channel_id,
                guild_id,
                user_id,
                int(datetime.utcnow().timestamp())
            )
        )

        await db.commit()


async def remove_ticket(channel_id):

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            DELETE FROM active_tickets
            WHERE channel_id = ?
            """,
            (channel_id,)
        )

        await db.commit()


# =========================
# TRANSCRIPT
# =========================

async def build_transcript(channel: discord.TextChannel):

    messages = []

    async for message in channel.history(limit=None, oldest_first=True):

        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M")

        content = (
            message.content
            if message.content
            else "[Embed/Attachment]"
        )

        messages.append(
            f"[{timestamp}] {message.author} : {content}"
        )

    transcript = "\n".join(messages)

    return io.BytesIO(transcript.encode()), f"{channel.name}.txt"


# =========================
# OPEN TICKET VIEW
# =========================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.blurple,
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
        # BLACKLIST
        # =========================

        blacklisted = await is_blacklisted(
            guild.id,
            user.id
        )

        if blacklisted:

            return await interaction.response.send_message(
                "❌ You are blacklisted from tickets.",
                ephemeral=True
            )

        # =========================
        # DUPLICATE CHECK
        # =========================

        existing = await get_open_ticket(
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
        # SETTINGS
        # =========================

        settings = await get_ticket_settings(
            guild.id
        )

        if not settings:

            return await interaction.response.send_message(
                "❌ Ticket system is not setup.",
                ephemeral=True
            )

        (
            category_id,
            log_channel_id,
            panel_channel,
            support_role_id
        ) = settings

        category = guild.get_channel(category_id)

        support_role = guild.get_role(
            support_role_id
        )

        # =========================
        # OVERWRITES
        # =========================

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True
                ),

            guild.me:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True
                )
        }

        if support_role:

            overwrites[support_role] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
            )

        # =========================
        # TICKET COUNT
        # =========================

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT count
                FROM ticket_counter
                WHERE guild_id = ?
                """,
                (guild.id,)
            ) as cursor:

                data = await cursor.fetchone()

            if not data:

                count = 1

                await db.execute(
                    """
                    INSERT INTO ticket_counter
                    (guild_id, count)
                    VALUES (?, ?)
                    """,
                    (guild.id, count)
                )

            else:

                count = data[0] + 1

                await db.execute(
                    """
                    UPDATE ticket_counter
                    SET count = ?
                    WHERE guild_id = ?
                    """,
                    (count, guild.id)
                )

            await db.commit()

        # =========================
        # CREATE CHANNEL
        # =========================

        channel = await guild.create_text_channel(
            name=f"ticket-{count}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket Owner: {user.id}"
        )

        # =========================
        # SAVE DATABASE
        # =========================

        await save_ticket(
            channel.id,
            guild.id,
            user.id
        )

        # =========================
        # EMBED
        # =========================

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=(
                f"Welcome {user.mention}\n\n"
                "Please explain your issue.\n"
                "Staff will assist you shortly."
            ),
            color=TICKET_COLOR
        )

        embed.add_field(
            name="Ticket Owner",
            value=user.mention
        )

        embed.set_footer(
            text="Dem Ticket System"
        )

        await channel.send(
            content=(
                f"{user.mention} "
                f"{support_role.mention if support_role else ''}"
            ),
            embed=embed,
            view=TicketControls()
        )

        # =========================
        # RESPONSE
        # =========================

        await interaction.response.send_message(
            f"✅ Created ticket: {channel.mention}",
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
# TICKET CONTROLS
# =========================

class TicketControls(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # =========================
    # CLOSE
    # =========================

    @discord.ui.button(
        label="Close",
        emoji="🔒",
        style=discord.ButtonStyle.red,
        custom_id="ticket_close"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_message(
            "🔒 Closing ticket..."
        )

        channel = interaction.channel

        # =========================
        # TRANSCRIPT
        # =========================

        file_data, filename = await build_transcript(
            channel
        )

        transcript = discord.File(
            file_data,
            filename=filename
        )

        # =========================
        # LOG CHANNEL
        # =========================

        settings = await get_ticket_settings(
            interaction.guild.id
        )

        if settings:

            log_channel_id = settings[1]

            log_channel = interaction.guild.get_channel(
                log_channel_id
            )

            if log_channel:

                await log_channel.send(
                    content=(
                        f"📁 Transcript for {channel.name}"
                    ),
                    file=transcript
                )

        # =========================
        # REMOVE DATABASE
        # =========================

        await remove_ticket(channel.id)

        # =========================
        # LOGGING
        # =========================

        await dispatch_log(
            interaction.guild,
            "ticket_close",
            (
                f"🔒 Ticket Closed\n"
                f"Channel: {channel.name}\n"
                f"Closed By: {interaction.user}"
            ),
            user_id=interaction.user.id
        )

        await asyncio.sleep(3)

        await channel.delete()

    # =========================
    # CLAIM
    # =========================

    @discord.ui.button(
        label="Claim",
        emoji="🛠️",
        style=discord.ButtonStyle.green,
        custom_id="ticket_claim"
    )
    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_message(
            f"🛠️ {interaction.user.mention} claimed this ticket."
        )

    # =========================
    # TRANSCRIPT BUTTON
    # =========================

    @discord.ui.button(
        label="Transcript",
        emoji="📄",
        style=discord.ButtonStyle.gray,
        custom_id="ticket_transcript"
    )
    async def transcript_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        file_data, filename = await build_transcript(
            interaction.channel
        )

        file = discord.File(
            file_data,
            filename=filename
        )

        await interaction.response.send_message(
            file=file,
            ephemeral=True
        )


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
        description="Ticket system commands."
    )
    @commands.has_permissions(
        administrator=True
    )
    async def ticket(self, ctx):

        if ctx.invoked_subcommand is None:

            await ctx.send_help(ctx.command)

    # =========================
    # SETUP
    # =========================

    @ticket.command(
        name="setup",
        description="Setup ticket system."
    )
    async def ticket_setup(
        self,
        ctx,
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        support_role: discord.Role
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT OR REPLACE INTO ticket_settings
                (
                    guild_id,
                    category_id,
                    log_channel,
                    panel_channel,
                    support_role
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ctx.guild.id,
                    category.id,
                    log_channel.id,
                    ctx.channel.id,
                    support_role.id
                )
            )

            await db.commit()

        embed = discord.Embed(
            title="🎫 Support Center",
            description=(
                "Need help?\n"
                "Click the button below to create a ticket."
            ),
            color=TICKET_COLOR
        )

        embed.set_footer(
            text="Dem Ticket System"
        )

        await ctx.send(
            embed=embed,
            view=TicketView()
        )

        await ctx.send(
            "✅ Ticket system configured."
        )

    # =========================
    # ADD USER
    # =========================

    @ticket.command(
        name="add",
        description="Add a user to ticket."
    )
    async def ticket_add(
        self,
        ctx,
        member: discord.Member
    ):

        await ctx.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

        await ctx.send(
            f"✅ Added {member.mention} to ticket."
        )

    # =========================
    # REMOVE USER
    # =========================

    @ticket.command(
        name="remove",
        description="Remove user from ticket."
    )
    async def ticket_remove(
        self,
        ctx,
        member: discord.Member
    ):

        await ctx.channel.set_permissions(
            member,
            overwrite=None
        )

        await ctx.send(
            f"✅ Removed {member.mention} from ticket."
        )

    # =========================
    # RENAME
    # =========================

    @ticket.command(
        name="rename",
        description="Rename ticket channel."
    )
    async def ticket_rename(
        self,
        ctx,
        *,
        name: str
    ):

        await ctx.channel.edit(
            name=name
        )

        await ctx.send(
            f"✅ Ticket renamed to `{name}`"
        )

    # =========================
    # BLACKLIST
    # =========================

    @ticket.command(
        name="blacklist"
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
            f"🚫 {user.mention} blacklisted."
        )

    # =========================
    # UNBLACKLIST
    # =========================

    @ticket.command(
        name="unblacklist"
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
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    ctx.guild.id,
                    user.id
                )
            )

            await db.commit()

        await ctx.send(
            f"✅ Removed blacklist from {user.mention}"
        )

    # =========================
    # STATS
    # =========================

    @ticket.command(
        name="stats"
    )
    async def ticket_stats(self, ctx):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT COUNT(*)
                FROM active_tickets
                WHERE guild_id = ?
                """,
                (ctx.guild.id,)
            ) as cursor:

                active = (await cursor.fetchone())[0]

        embed = discord.Embed(
            title="🎫 Ticket Statistics",
            color=TICKET_COLOR
        )

        embed.add_field(
            name="Active Tickets",
            value=str(active)
        )

        await ctx.send(embed=embed)


# =========================
# LOAD
# =========================

async def setup(bot):

    await bot.add_cog(
        Tickets(bot)
    )
