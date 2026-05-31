import re
import time
import discord

from datetime import timedelta
from collections import defaultdict, deque
from discord.ext import commands

from utils.database import get_db
from utils.dispatch import dispatch_log


DEFAULTS = {
    "spam": (1, 6, "timeout"),
    "caps": (1, 70, "warn"),
    "mentions": (1, 5, "timeout"),
    "duplicate": (1, 3, "timeout"),
    "invite": (1, 1, "timeout"),
    "scam": (1, 1, "ban"),
    "toxicity": (1, 1, "warn"),
    "ghostping": (1, 1, "warn"),
    "raid": (1, 3, "kick"),
    "media": (0, 1, "warn"),
    "linkspam": (1, 3, "timeout"),
    "emoji_spam": (1, 12, "warn")
}

TOXIC_WORDS = [
    "kys",
    "kill yourself",
    "retard",
    "fatherless",
    "loser",
    "idiot",
    "stupid"
]

SCAM_WORDS = [
    "free nitro",
    "steam gift",
    "claim reward",
    "free robux",
    "bitcoin giveaway",
    "airdrop",
    "crypto reward",
    "discord gift"
]

INVITE_REGEX = r"(discord\.gg\/|discord\.com\/invite\/)"
LINK_REGEX = r"(https?:\/\/[^\s]+)"
EMOJI_REGEX = r"<a?:\w+:\d+>"


class VerifyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.green,
        emoji="✅",
        custom_id="dem_verify_button"
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        async with await get_db() as db:

            cursor = await db.execute(
                """
                SELECT role_id
                FROM verification
                WHERE guild_id=?
                """,
                (interaction.guild.id,)
            )

            data = await cursor.fetchone()
            await cursor.close()

        if not data:

            return await interaction.response.send_message(
                "Verification not configured.",
                ephemeral=True
            )

        role = interaction.guild.get_role(
            data["role_id"]
        )

        if not role:

            return await interaction.response.send_message(
                "Verification role missing.",
                ephemeral=True
            )

        if role in interaction.user.roles:

            return await interaction.response.send_message(
                "Already verified.",
                ephemeral=True
            )

        try:

            await interaction.user.add_roles(
                role,
                reason="Verification"
            )

            await interaction.response.send_message(
                "Verified successfully.",
                ephemeral=True
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "Failed to verify.",
                ephemeral=True
            )


class AdvancedAutomod(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.spam_cache = defaultdict(deque)

        self.duplicate_cache = defaultdict(int)

        self.last_message = {}

        self.ghost_ping = {}

        self.join_cache = defaultdict(deque)

    async def cog_load(self):

        self.bot.add_view(
            VerifyView()
        )

    async def get_feature(
        self,
        guild_id,
        feature
    ):

        async with await get_db() as db:

            cursor = await db.execute(
                """
                SELECT enabled,
                       limit_value,
                       punishment
                FROM automod_settings
                WHERE guild_id=?
                AND feature=?
                """,
                (
                    guild_id,
                    feature
                )
            )

            data = await cursor.fetchone()

            await cursor.close()

        return data if data else DEFAULTS[
            feature
        ]

    async def is_whitelisted(
        self,
        guild_id,
        user_id
    ):

        async with await get_db() as db:

            cursor = await db.execute(
                """
                SELECT 1
                FROM automod_whitelist
                WHERE guild_id=?
                AND user_id=?
                """,
                (
                    guild_id,
                    user_id
                )
            )

            data = await cursor.fetchone()

            await cursor.close()

            return data is not None

    async def add_warn(
        self,
        guild_id,
        user_id
    ):

        async with await get_db() as db:

            cursor = await db.execute(
                """
                SELECT warns
                FROM automod_warns
                WHERE guild_id=?
                AND user_id=?
                """,
                (
                    guild_id,
                    user_id
                )
            )

            data = await cursor.fetchone()

            warns = (
                data["warns"]
                if data
                else 0
            ) + 1

            await cursor.close()

            await db.execute(
                """
                INSERT OR REPLACE
                INTO automod_warns
                VALUES (?, ?, ?)
                """,
                (
                    guild_id,
                    user_id,
                    warns
                )
            )

            await db.commit()

        return warns

    async def execute_punishment(
        self,
        member,
        punishment,
        reason
    ):

        try:

            me = (
                member.guild.me
                or
                member.guild.get_member(
                    self.bot.user.id
                )
            )

            if not me:
                return

            if (
                member == member.guild.owner
                or
                member.top_role >= me.top_role
            ):
                return

            if punishment == "warn":

                warns = await self.add_warn(
                    member.guild.id,
                    member.id
                )

                try:

                    await member.send(
                        f"Warning\n"
                        f"Reason: {reason}\n"
                        f"Warns: {warns}"
                    )

                except discord.HTTPException:

                    pass

            elif punishment == "timeout":

                await member.timeout(
                    discord.utils.utcnow()
                    + timedelta(
                        minutes=10
                    ),
                    reason=reason
                )

            elif punishment == "kick":

                await member.kick(
                    reason=reason
                )

            elif punishment == "ban":

                await member.ban(
                    reason=reason
                )

            await dispatch_log(

                member.guild,

                "automod",

                content=(
                    f"User: {member}\n"
                    f"Punishment: {punishment}\n"
                    f"Reason: {reason}"
                ),

                user_id=member.id
            )

        except Exception as e:

            print(e)

    @commands.Cog.listener()
    async def on_message(
        self,
        message
    ):

        if not message.guild:
            return

        if message.author.bot:
            return

        if message.author.guild_permissions.manage_messages:
            return

        if await self.is_whitelisted(
            message.guild.id,
            message.author.id
        ):
            return

        uid = message.author.id

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "spam"
        )

        if enabled:

            now = time.time()

            self.spam_cache[
                uid
            ].append(now)

            while (
                self.spam_cache[uid]
                and
                now - self.spam_cache[uid][0] > 5
            ):

                self.spam_cache[
                    uid
                ].popleft()

            if len(
                self.spam_cache[uid]
            ) >= limit:

                try:

                    await message.delete()

                except discord.HTTPException:

                    pass

                await self.execute_punishment(

                    message.author,

                    punishment,

                    "Spam detected"

                )

                return

        self.ghost_ping[
            message.id
        ] = (

            message.author.id,

            [
                m.id
                for m in message.mentions
            ]

        )

    @commands.Cog.listener()
    async def on_message_delete(
        self,
        message
    ):

        data = self.ghost_ping.pop(
            message.id,
            None
        )

        if not data:
            return

        author_id, mentions = data

        if not mentions:
            return

        member = message.guild.get_member(
            author_id
        )

        if not member:
            return

        enabled, limit, punishment = await self.get_feature(

            message.guild.id,

            "ghostping"

        )

        if not enabled:
            return

        await self.execute_punishment(

            member,

            punishment,

            "Ghost Ping Detected"

        )


async def setup(bot):

    await bot.add_cog(
        AdvancedAutomod(bot)
    )
