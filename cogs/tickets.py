import io
import asyncio
import discord

from datetime import datetime
from discord.ext import commands

from utils.database import get_db
from utils.dispatch import dispatch_log
from utils.embeds import (
    success_embed,
    base_embed
)


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


async def build_transcript(channel):

    lines=[]

    async for msg in channel.history(
        oldest_first=True
    ):

        lines.append(

            f"[{msg.created_at}] "

            f"{msg.author}: "

            f"{msg.content}"

        )

    return io.BytesIO(
        "\n".join(lines).encode()
    )


class TicketView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Open Ticket",
        emoji="🎫",
        custom_id="dem_ticket_open"
    )

    async def open_ticket(
        self,
        interaction,
        button
    ):

        existing=await get_open_ticket(

            interaction.guild.id,

            interaction.user.id

        )

        if existing:

            return await interaction.response.send_message(

                "You already have a ticket.",

                ephemeral=True

            )

        settings=await get_ticket_settings(

            interaction.guild.id

        )

        if not settings:

            return await interaction.response.send_message(

                "Ticket system not setup.",

                ephemeral=True

            )

        category_id,log_channel,panel,support=settings

        channel=await interaction.guild.create_text_channel(

            name=f"ticket-{interaction.user.name}",

            category=interaction.guild.get_channel(
                category_id
            )

        )

        async with await get_db() as db:

            await db.execute(

                "INSERT INTO active_tickets VALUES(?,?,?,?)",

                (

                    channel.id,

                    interaction.guild.id,

                    interaction.user.id,

                    int(datetime.utcnow().timestamp())

                )

            )

            await db.commit()

        await channel.send(

            embed=base_embed(

                title="Ticket Created",

                description="Describe your issue."

            ),

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

        transcript=await build_transcript(
            interaction.channel
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

        await interaction.channel.delete()


class Tickets(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot=bot

    async def cog_load(self):

        self.bot.add_view(
            TicketView()
        )

        self.bot.add_view(
            TicketControls()
        )

    @commands.hybrid_group()

    async def ticket(
        self,
        ctx
    ):

        if ctx.invoked_subcommand is None:

            await ctx.send_help(
                ctx.command
            )

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

                description="Press below"

            ),

            view=TicketView()

        )

        await ctx.send(

            embed=success_embed(
                "Ticket configured."
            )

        )


async def setup(bot):

    await bot.add_cog(
        Tickets(bot)
    )
