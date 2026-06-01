import random
import time
import asyncio
import aiosqlite
import discord

from discord.ext import commands, tasks
from discord import app_commands

from utils.database import DB_PATH
from utils.config import BRAND_COLOR
from utils.dispatch import dispatch_log


class GiveawayView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Join Giveaway",
        emoji="🎉",
        style=discord.ButtonStyle.blurple,
        custom_id="dem_giveaway_join"
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT req_role,
                black_role
                FROM giveaways
                WHERE message_id=?
                """,
                (interaction.message.id,)
            ) as cursor:

                data = await cursor.fetchone()

        if not data:

            return await interaction.response.send_message(
                "This giveaway ended.",
                ephemeral=True
            )

        req_role, black_role = data

        if black_role:

            role = interaction.guild.get_role(
                black_role
            )

            if role and role in interaction.user.roles:

                return await interaction.response.send_message(
                    "You cannot join this giveaway.",
                    ephemeral=True
                )

        if req_role:

            role = interaction.guild.get_role(
                req_role
            )

            if role and role not in interaction.user.roles:

                return await interaction.response.send_message(
                    f"You need {role.mention}",
                    ephemeral=True
                )

        async with aiosqlite.connect(DB_PATH) as db:

            try:

                await db.execute(
                    """
                    INSERT INTO giveaway_entries
                    VALUES (?,?)
                    """,
                    (
                        interaction.message.id,
                        interaction.user.id
                    )
                )

                await db.commit()

            except:

                return await interaction.response.send_message(
                    "You already joined.",
                    ephemeral=True
                )

        await interaction.response.send_message(
            "Joined giveaway.",
            ephemeral=True
        )


class Giveaways(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.giveaway_loop.start()

        bot.add_view(
            GiveawayView()
        )

    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaways(
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER,
                channel_id INTEGER,
                prize TEXT,
                winners INTEGER,
                end_time INTEGER,
                ended INTEGER DEFAULT 0,
                req_role INTEGER,
                black_role INTEGER
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_entries(
                message_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY(message_id,user_id)
            )
            """)

            await db.commit()

    def cog_unload(self):

        self.giveaway_loop.cancel()

    def parse_time(self, text):

        values = {

            "s":1,
            "m":60,
            "h":3600,
            "d":86400

        }

        try:

            return int(
                text[:-1]
            ) * values[
                text[-1].lower()
            ]

        except:

            return None

    @tasks.loop(
        seconds=15
    )
    async def giveaway_loop(self):

        now = int(
            time.time()
        )

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT *
                FROM giveaways
                WHERE ended=0
                AND end_time<=?
                """,
                (now,)
            ) as cursor:

                data = await cursor.fetchall()

        for giveaway in data:

            await self.finish_giveaway(
                giveaway
            )

    async def finish_giveaway(
        self,
        giveaway
    ):

        (
            message_id,
            guild_id,
            channel_id,
            prize,
            winners_count,
            _,
            _,
            _,
            _
        ) = giveaway

        guild = self.bot.get_guild(
            guild_id
        )

        if not guild:
            return

        channel = guild.get_channel(
            channel_id
        )

        if not channel:
            return

        try:

            message = await channel.fetch_message(
                message_id
            )

        except:

            return

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT user_id
                FROM giveaway_entries
                WHERE message_id=?
                """,
                (message_id,)
            ) as cursor:

                users = await cursor.fetchall()

            await db.execute(
                """
                UPDATE giveaways
                SET ended=1
                WHERE message_id=?
                """,
                (message_id,)
            )

            await db.commit()

        members = []

        for row in users:

            member = guild.get_member(
                row[0]
            )

            if member:

                members.append(
                    member
                )

        if not members:

            return await channel.send(
                f"No winners for **{prize}**"
            )

        winners = random.sample(
            members,
            min(
                winners_count,
                len(members)
            )
        )

        mentions = ", ".join(
            x.mention
            for x in winners
        )

        embed = discord.Embed(

            title="🎉 Giveaway Ended",

            description=(
                f"Prize: **{prize}**\n"
                f"Winners: {mentions}"
            ),

            color=discord.Color.gold()

        )

        await channel.send(

            content=f"Congratulations {mentions}",

            embed=embed

        )

        await dispatch_log(

            guild,

            "giveaway",

            content=(
                f"Prize: {prize}\n"
                f"Winners: {mentions}"
            )

        )

    @commands.hybrid_command(
        name="gstart"
    )
    @commands.has_permissions(
        manage_guild=True
    )
    async def gstart(

        self,

        ctx,

        duration:str,

        winners:int,

        prize:str,

        role_req:discord.Role=None,

        blacklist:discord.Role=None

    ):

        seconds = self.parse_time(
            duration
        )

        if not seconds:

            return await ctx.send(
                "Use: 10m / 1h / 1d"
            )

        end = int(
            time.time()
        ) + seconds

        embed = discord.Embed(

            title="🎉 Giveaway",

            description=(
                f"Prize: **{prize}**\n"
                f"Winners: **{winners}**\n"
                f"Ends: <t:{end}:R>"
            ),

            color=BRAND_COLOR

        )

        msg = await ctx.send(

            embed=embed,

            view=GiveawayView()

        )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT INTO giveaways
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    msg.id,
                    ctx.guild.id,
                    ctx.channel.id,
                    prize,
                    winners,
                    end,
                    0,
                    role_req.id if role_req else None,
                    blacklist.id if blacklist else None
                )
            )

            await db.commit()

        await ctx.send(
            "Giveaway started."
        )


async def setup(bot):

    await bot.add_cog(
        Giveaways(bot)
    )
