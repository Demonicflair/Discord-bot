import io
import asyncio
import discord

from datetime import datetime

from discord.ext import commands

from utils.database import get_db
from utils.dispatch import dispatch_log
from utils.embeds import (
    success_embed,
    error_embed,
    base_embed
)


TICKET_COLOR = 0x2B2D31


# =====================================
# HELPERS
# =====================================

async def get_ticket_settings(guild_id):

    async with await get_db() as db:

        async with db.execute(

            """
            SELECT

            category_id,
            log_channel,
            panel_channel,
            support_role

            FROM ticket_settings

            WHERE guild_id=?

            """,

            (guild_id,)

        ) as cursor:

            return await cursor.fetchone()


async def get_open_ticket(
    guild_id,
    user_id
):

    async with await get_db() as db:

        async with db.execute(

            """
            SELECT channel_id

            FROM active_tickets

            WHERE guild_id=?
            AND user_id=?

            """,

            (
                guild_id,
                user_id
            )

        ) as cursor:

            return await cursor.fetchone()


async def is_blacklisted(
    guild_id,
    user_id
):

    async with await get_db() as db:

        async with db.execute(

            """
            SELECT 1

            FROM ticket_blacklist

            WHERE guild_id=?
            AND user_id=?

            """,

            (
                guild_id,
                user_id
            )

        ) as cursor:

            return await cursor.fetchone()


async def next_ticket_number(
    guild_id
):

    async with await get_db() as db:

        await db.execute(

            """
            INSERT OR IGNORE
            INTO ticket_counter

            VALUES(?,0)

            """,

            (guild_id,)

        )

        await db.execute(

            """
            UPDATE ticket_counter

            SET count=count+1

            WHERE guild_id=?

            """,

            (guild_id,)

        )

        await db.commit()

        async with db.execute(

            """
            SELECT count

            FROM ticket_counter

            WHERE guild_id=?

            """,

            (guild_id,)

        ) as cursor:

            row=await cursor.fetchone()

            return row[0]


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

    return io.BytesIO(

        "\n".join(lines).encode()

    )


# =====================================
# OPEN BUTTON
# =====================================

class TicketView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(

        label="Open Ticket",

        emoji="🎫",

        style=discord.ButtonStyle.blurple,

        custom_id="dem_ticket_open"

    )

    async def open_ticket(

        self,
        interaction,
        button

    ):

        guild=interaction.guild
        user=interaction.user

        if await is_blacklisted(
            guild.id,
            user.id
        ):

            return await interaction.response.send_message(

                "You cannot create tickets.",

                ephemeral=True

            )

        existing=await get_open_ticket(

            guild.id,

            user.id

        )

        if existing:

            channel=guild.get_channel(
                existing[0]
            )

            if channel:

                return await interaction.response.send_message(

                    f"You already have {channel.mention}",

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

        category_id,log_channel,panel_channel,support_role=settings

        number=await next_ticket_number(
            guild.id
        )

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

            name=f"ticket-{number}",

            category=guild.get_channel(
                category_id
            ),

            overwrites=overwrites

        )

        async with await get_db() as db:

            await db.execute(

                """
                INSERT INTO active_tickets

                VALUES(?,?,?,?)

                """,

                (

                    channel.id,

                    guild.id,

                    user.id,

                    int(datetime.utcnow().timestamp())

                )

            )

            await db.commit()

        await channel.send(

            embed=base_embed(

                title="Ticket Created",

                description=(
                    f"{user.mention}\n"
                    "Describe your issue."
                )

            ),

            view=TicketControls()

        )

        await interaction.response.send_message(

            f"Created {channel.mention}",

            ephemeral=True

        )


# =====================================
# CLOSE BUTTON
# =====================================

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

        transcript=await build_transcript(

            interaction.channel

        )

        settings=await get_ticket_settings(

            interaction.guild.id

        )

        if settings:

            log_channel=interaction.guild.get_channel(

                settings[1]

            )

            if log_channel:

                await log_channel.send(

                    content=f"Transcript {interaction.channel.name}",

                    file=discord.File(

                        transcript,

                        filename=f"{interaction.channel.name}.txt"

                    )

                )

        async with await get_db() as db:

            await db.execute(

                """
                DELETE FROM active_tickets

                WHERE channel_id=?

                """,

                (interaction.channel.id,)

            )

            await db.commit()

        await dispatch_log(

            interaction.guild,

            "ticket_close",

            content=f"{interaction.channel.name} closed",

            user_id=interaction.user.id

        )

        await asyncio.sleep(2)

        await interaction.channel.delete()


# =====================================
# COG
# =====================================

class Tickets(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot=bot

    @commands.hybrid_group()

    @commands.has_permissions(
        administrator=True
    )

    async def ticket(
        self,
        ctx
    ):

        pass

    @ticket.command()

    async def setup(

        self,

        ctx,

        category:discord.CategoryChannel,

        log_channel:discord.TextChannel,

        support_role:discord.Role

    ):

        async with await get_db() as db:

            await db.execute(

                """
                INSERT OR REPLACE

                INTO ticket_settings

                VALUES(?,?,?,?,?)

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

        await ctx.send(

            embed=base_embed(

                title="Support Center",

                description="Press below."

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
