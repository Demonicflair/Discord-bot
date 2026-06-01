# cogs/tickets.py

import io
import asyncio
import discord

from datetime import datetime
from discord.ext import commands
from discord import app_commands

from utils.database import (
    get_db,
    DB_PATH
)

from utils.dispatch import dispatch_log
from utils.embeds import (
    success_embed,
    error_embed,
    base_embed
)


TICKET_COLOR = 0x2b2d31


# ====================================
# HELPERS
# ====================================

async def get_ticket_settings(guild_id):

    db = await get_db()

    async with db.execute("""

    SELECT
    category_id,
    log_channel,
    panel_channel,
    support_role

    FROM ticket_settings

    WHERE guild_id=?

    """,(guild_id,)) as cursor:

        data = await cursor.fetchone()

    await db.close()

    return data


async def get_open_ticket(
    guild_id,
    user_id
):

    db = await get_db()

    async with db.execute("""

    SELECT channel_id

    FROM active_tickets

    WHERE guild_id=?
    AND user_id=?

    """,(guild_id,user_id)) as cursor:

        data = await cursor.fetchone()

    await db.close()

    return data


async def build_transcript(channel):

    lines=[]

    async for msg in channel.history(
        oldest_first=True,
        limit=None
    ):

        content=msg.content

        if not content:

            if msg.attachments:

                content="[Attachment]"

            elif msg.embeds:

                content="[Embed]"

            else:

                content="[Empty]"

        lines.append(

            f"[{msg.created_at}] "

            f"{msg.author}: "

            f"{content}"

        )

    text="\n".join(lines)

    return io.BytesIO(
        text.encode()
    )


# ====================================
# TICKET VIEW
# ====================================

class TicketView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Open Ticket",
        emoji="🎫",
        custom_id="dem_ticket_open",
        style=discord.ButtonStyle.blurple
    )

    async def open_ticket(

        self,
        interaction,
        button

    ):

        guild=interaction.guild
        user=interaction.user

        existing=await get_open_ticket(
            guild.id,
            user.id
        )

        if existing:

            ch=guild.get_channel(
                existing[0]
            )

            if ch:

                return await interaction.response.send_message(

                    f"You already have {ch.mention}",

                    ephemeral=True

                )

        settings=await get_ticket_settings(
            guild.id
        )

        if not settings:

            return await interaction.response.send_message(

                "Ticket system not configured.",

                ephemeral=True

            )

        category_id,log_channel,panel,support_role=settings

        overwrites={

            guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

            user:
            discord.PermissionOverwrite(

                view_channel=True,

                send_messages=True,

                read_message_history=True

            ),

            guild.me:
            discord.PermissionOverwrite(

                view_channel=True,

                manage_channels=True

            )

        }

        role=guild.get_role(
            support_role
        )

        if role:

            overwrites[role]=discord.PermissionOverwrite(

                view_channel=True,

                send_messages=True

            )

        channel=await guild.create_text_channel(

            name=f"ticket-{user.name}",

            overwrites=overwrites,

            category=guild.get_channel(
                category_id
            )

        )

        db=await get_db()

        await db.execute("""

        INSERT OR REPLACE INTO active_tickets

        VALUES(?,?,?,?)

        """,(

            channel.id,

            guild.id,

            user.id,

            int(datetime.utcnow().timestamp())

        ))

        await db.commit()

        await db.close()

        embed=base_embed(

            title="Ticket Created",

            description=(
                f"{user.mention}\n"
                "Describe your issue."
            )

        )

        await channel.send(

            embed=embed,

            view=TicketControls()

        )

        await interaction.response.send_message(

            f"Created {channel.mention}",

            ephemeral=True

        )


class TicketControls(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(

        label="Close",

        style=discord.ButtonStyle.red,

        custom_id="ticket_close"

    )

    async def close(

        self,
        interaction,
        button

    ):

        await interaction.response.defer()

        channel=interaction.channel

        transcript=await build_transcript(
            channel
        )

        file=discord.File(

            transcript,

            filename=f"{channel.name}.txt"

        )

        settings=await get_ticket_settings(
            interaction.guild.id
        )

        if settings:

            log=interaction.guild.get_channel(
                settings[1]
            )

            if log:

                await log.send(

                    file=file,

                    content=f"Transcript {channel.name}"

                )

        db=await get_db()

        await db.execute("""

        DELETE FROM active_tickets

        WHERE channel_id=?

        """,(channel.id,))

        await db.commit()

        await db.close()

        await dispatch_log(

            interaction.guild,

            "ticket_close",

            content=f"{channel.name} closed",

            user_id=interaction.user.id

        )

        await asyncio.sleep(2)

        await channel.delete()


# ====================================
# COG
# ====================================

class Tickets(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot=bot

    async def cog_load(self):

        db=await get_db()

        await db.execute("""

        CREATE TABLE IF NOT EXISTS ticket_blacklist(

        guild_id INTEGER,
        user_id INTEGER,

        PRIMARY KEY(
        guild_id,
        user_id)

        )

        """)

        await db.execute("""

        CREATE TABLE IF NOT EXISTS ticket_counter(

        guild_id INTEGER PRIMARY KEY,

        count INTEGER

        )

        """)

        await db.commit()

        await db.close()

        self.bot.add_view(
            TicketView()
        )

        self.bot.add_view(
            TicketControls()
        )

    @commands.hybrid_group(
        name="ticket"
    )

    @commands.has_permissions(
        administrator=True
    )

    async def ticket(
        self,
        ctx
    ):

        if ctx.invoked_subcommand is None:

            await ctx.send_help(
                ctx.command
            )

    @ticket.command(
        name="setup"
    )

    async def setup_ticket(

        self,

        ctx,

        category:discord.CategoryChannel,

        log_channel:discord.TextChannel,

        support_role:discord.Role

    ):

        db=await get_db()

        await db.execute("""

        INSERT OR REPLACE INTO ticket_settings

        VALUES(?,?,?,?,?)

        """,(

            ctx.guild.id,

            category.id,

            log_channel.id,

            ctx.channel.id,

            support_role.id

        ))

        await db.commit()

        await db.close()

        await ctx.send(

            embed=base_embed(

                title="Support Center",

                description="Press button below."

            ),

            view=TicketView()

        )

        await ctx.send(

            embed=success_embed(
                "Ticket system configured."
            )

        )


async def setup(bot):

    await bot.add_cog(
        Tickets(bot)
    )
