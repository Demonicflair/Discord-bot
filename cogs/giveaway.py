# giveaway.py

import discord
from discord.ext import commands
import sqlite3
import asyncio
import random
import time

from utils.logger import get_logs, save_log, is_log_enabled

# =========================
# DATABASE
# =========================
db = sqlite3.connect("giveaways.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS giveaways(
    message_id INTEGER,
    guild_id INTEGER,
    channel_id INTEGER,
    prize TEXT,
    winners INTEGER,
    end_time INTEGER,
    ended INTEGER
)
""")

db.commit()

# =========================
# LOG SYSTEM
# =========================
async def send_log(guild, text):

    logs = get_logs(guild.id)

    if logs and is_log_enabled(guild.id, "giveaway"):

        channel = guild.get_channel(logs[1])

        if channel:
            embed = discord.Embed(
                description=text,
                color=discord.Color.blurple()
            )

            await channel.send(embed=embed)

    save_log(guild.id, 0, "giveaway", text)


# =========================
# GIVEAWAY BUTTON
# =========================
class GiveawayButton(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎉 Join Giveaway",
        style=discord.ButtonStyle.green,
        custom_id="giveaway_join"
    )
    async def join(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        message = interaction.message

        users = [
            user async for user in message.reactions[0].users()
            if not user.bot
        ]

        if interaction.user in users:

            return await interaction.response.send_message(
                "❌ You already joined.",
                ephemeral=True
            )

        await message.add_reaction("🎉")

        await interaction.response.send_message(
            "✅ Joined giveaway!",
            ephemeral=True
        )


# =========================
# GIVEAWAY COG
# =========================
class Giveaway(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.bot.loop.create_task(self.giveaway_loop())

    # =========================
    # GIVEAWAY LOOP
    # =========================
    async def giveaway_loop(self):

        await self.bot.wait_until_ready()

        while not self.bot.is_closed():

            now = int(time.time())

            cursor.execute(
                "SELECT * FROM giveaways WHERE ended=0"
            )

            giveaways = cursor.fetchall()

            for g in giveaways:

                message_id = g[0]
                guild_id = g[1]
                channel_id = g[2]
                prize = g[3]
                winner_count = g[4]
                end_time = g[5]

                if now >= end_time:

                    guild = self.bot.get_guild(guild_id)

                    if not guild:
                        continue

                    channel = guild.get_channel(channel_id)

                    if not channel:
                        continue

                    try:

                        message = await channel.fetch_message(message_id)

                    except:
                        continue

                    users = []

                    for reaction in message.reactions:

                        if reaction.emoji == "🎉":

                            users = [
                                user async for user in reaction.users()
                                if not user.bot
                            ]

                    if not users:

                        embed = discord.Embed(
                            title="🎉 Giveaway Ended",
                            description=f"Prize: **{prize}**\nNo winners.",
                            color=discord.Color.red()
                        )

                        await channel.send(embed=embed)

                    else:

                        winners = random.sample(
                            users,
                            min(winner_count, len(users))
                        )

                        mentions = ", ".join(
                            w.mention for w in winners
                        )

                        embed = discord.Embed(
                            title="🎉 Giveaway Ended",
                            description=(
                                f"🏆 Prize: **{prize}**\n"
                                f"🎊 Winner(s): {mentions}"
                            ),
                            color=discord.Color.green()
                        )

                        await channel.send(embed=embed)

                        await send_log(
                            guild,
                            f"🎉 Giveaway ended → {prize}"
                        )

                    cursor.execute(
                        "UPDATE giveaways SET ended=1 WHERE message_id=?",
                        (message_id,)
                    )

                    db.commit()

            await asyncio.sleep(10)

    # =========================
    # START GIVEAWAY
    # =========================
    @commands.hybrid_command(
        name="giveaway",
        help="Start a giveaway.",
        extras={
            "example": "!giveaway 60 1 Nitro",
            "tips": "Time is in seconds."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def giveaway(
        self,
        ctx,
        duration: int = None,
        winners: int = 1,
        *,
        prize=None
    ):
        """Start a giveaway."""

        if duration is None or prize is None:

            return await ctx.send(
                "❌ Usage: !giveaway <seconds> <winners> <prize>"
            )

        end = int(time.time()) + duration

        embed = discord.Embed(
            title="🎉 Giveaway",
            description=(
                f"🏆 Prize: **{prize}**\n"
                f"👑 Winners: **{winners}**\n"
                f"⏰ Ends: <t:{end}:R>\n\n"
                f"Click the button below to join!"
            ),
            color=discord.Color.blurple()
        )

        msg = await ctx.send(
            embed=embed,
            view=GiveawayButton()
        )

        await msg.add_reaction("🎉")

        cursor.execute(
            "INSERT INTO giveaways VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                msg.id,
                ctx.guild.id,
                ctx.channel.id,
                prize,
                winners,
                end,
                0
            )
        )

        db.commit()

        await send_log(
            ctx.guild,
            f"🎉 Giveaway started → {prize}"
        )

    # =========================
    # REROLL
    # =========================
    @commands.hybrid_command(
        name="reroll",
        help="Reroll a giveaway.",
        extras={
            "example": "!reroll 123456789",
            "tips": "Use giveaway message ID."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def reroll(
        self,
        ctx,
        message_id: int = None
    ):
        """Reroll a giveaway."""

        if not message_id:

            return await ctx.send(
                "❌ Usage: !reroll <message_id>"
            )

        try:

            message = await ctx.channel.fetch_message(message_id)

        except:

            return await ctx.send(
                "❌ Giveaway not found."
            )

        users = []

        for reaction in message.reactions:

            if reaction.emoji == "🎉":

                users = [
                    user async for user in reaction.users()
                    if not user.bot
                ]

        if not users:

            return await ctx.send(
                "❌ No valid users."
            )

        winner = random.choice(users)

        embed = discord.Embed(
            title="🎉 Giveaway Rerolled",
            description=f"🏆 New Winner: {winner.mention}",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    # =========================
    # END GIVEAWAY
    # =========================
    @commands.hybrid_command(
        name="endgiveaway",
        help="Force end a giveaway.",
        extras={
            "example": "!endgiveaway 123456789",
            "tips": "Ends instantly."
        }
    )
    @commands.has_permissions(manage_guild=True)
    async def endgiveaway(
        self,
        ctx,
        message_id: int = None
    ):
        """End giveaway early."""

        if not message_id:

            return await ctx.send(
                "❌ Usage: !endgiveaway <message_id>"
            )

        cursor.execute(
            "UPDATE giveaways SET end_time=? WHERE message_id=?",
            (1, message_id)
        )

        db.commit()

        await ctx.send("✅ Giveaway ending shortly.")


# =========================
# SETUP
# =========================
async def setup(bot):

    bot.add_view(GiveawayButton())

    await bot.add_cog(Giveaway(bot))
