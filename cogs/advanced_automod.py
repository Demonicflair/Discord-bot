import re
import time
import asyncio
import discord
import aiosqlite

from collections import defaultdict, deque
from discord.ext import commands

from utils.database import DB_PATH
from utils.dispatch import dispatch_log

# =========================
# DEFAULT SETTINGS
# =========================

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

# =========================
# DETECTION LISTS
# =========================

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

# =========================
# VERIFY BUTTON
# =========================

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

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT role_id
                FROM verification
                WHERE guild_id=?
                """,
                (interaction.guild.id,)
            ) as cursor:

                data = await cursor.fetchone()

        if not data:
            return await interaction.response.send_message(
                "❌ Verification system not setup.",
                ephemeral=True
            )

        role = interaction.guild.get_role(data[0])

        if not role:
            return await interaction.response.send_message(
                "❌ Verification role missing.",
                ephemeral=True
            )

        try:
            await interaction.user.add_roles(role)

            await interaction.response.send_message(
                "✅ Verified successfully.",
                ephemeral=True
            )

        except Exception:
            await interaction.response.send_message(
                "❌ Failed to verify.",
                ephemeral=True
            )

# =========================
# ADVANCED AUTOMOD
# =========================

class AdvancedAutomod(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.spam_cache = defaultdict(deque)
        self.duplicate_cache = defaultdict(int)
        self.last_message = {}
        self.ghost_ping = {}
        self.join_cache = defaultdict(deque)

    # =========================
    # DATABASE INIT
    # =========================

    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_settings(
                guild_id INTEGER,
                feature TEXT,
                enabled INTEGER,
                limit_value INTEGER,
                punishment TEXT,
                PRIMARY KEY(guild_id, feature)
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_whitelist(
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY(guild_id, user_id)
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS automod_warns(
                guild_id INTEGER,
                user_id INTEGER,
                warns INTEGER DEFAULT 0,
                PRIMARY KEY(guild_id, user_id)
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS verification(
                guild_id INTEGER PRIMARY KEY,
                role_id INTEGER,
                channel_id INTEGER
            )
            """)

            await db.commit()

    # =========================
    # GET FEATURE
    # =========================

    async def get_feature(self, guild_id, feature):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT enabled, limit_value, punishment
                FROM automod_settings
                WHERE guild_id=? AND feature=?
                """,
                (guild_id, feature)
            ) as cursor:

                data = await cursor.fetchone()

        if data:
            return data

        return DEFAULTS[feature]

    # =========================
    # SET FEATURE
    # =========================

    async def set_feature(
        self,
        guild_id,
        feature,
        enabled,
        limit_value,
        punishment
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(
                """
                INSERT OR REPLACE INTO automod_settings
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    feature,
                    enabled,
                    limit_value,
                    punishment
                )
            )

            await db.commit()

    # =========================
    # WHITELIST CHECK
    # =========================

    async def is_whitelisted(
        self,
        guild_id,
        user_id
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT *
                FROM automod_whitelist
                WHERE guild_id=? AND user_id=?
                """,
                (guild_id, user_id)
            ) as cursor:

                data = await cursor.fetchone()

        return data is not None

    # =========================
    # WARN SYSTEM
    # =========================

    async def add_warn(
        self,
        guild_id,
        user_id
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute(
                """
                SELECT warns
                FROM automod_warns
                WHERE guild_id=? AND user_id=?
                """,
                (guild_id, user_id)
            ) as cursor:

                data = await cursor.fetchone()

            warns = (data[0] if data else 0) + 1

            await db.execute(
                """
                INSERT OR REPLACE INTO automod_warns
                VALUES (?, ?, ?)
                """,
                (guild_id, user_id, warns)
            )

            await db.commit()

        return warns

    # =========================
    # EXECUTE PUNISHMENT
    # =========================

    async def execute_punishment(
        self,
        member,
        punishment,
        reason
    ):

        try:

            if punishment == "warn":

                warns = await self.add_warn(
                    member.guild.id,
                    member.id
                )

                try:
                    await member.send(
                        f"⚠️ Warning in {member.guild.name}\n"
                        f"Reason: {reason}\n"
                        f"Warnings: {warns}"
                    )
                except:
                    pass

            elif punishment == "timeout":

                await member.timeout(
                    discord.utils.utcnow()
                    + discord.timedelta(minutes=10),
                    reason=reason
                )

            elif punishment == "kick":

                await member.kick(reason=reason)

            elif punishment == "ban":

                await member.ban(reason=reason)

            await dispatch_log(
                member.guild,
                "automod",
                content=(
                    f"🛡️ AutoMod Action\n"
                    f"User: {member}\n"
                    f"Punishment: {punishment}\n"
                    f"Reason: {reason}"
                ),
                user_id=member.id
            )

        except Exception as e:
            print(f"[AUTOMOD ERROR] {e}")

    # =========================
    # MESSAGE EVENT
    # =========================

    @commands.Cog.listener()
    async def on_message(self, message):

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

        content = message.content.lower()

        # =========================
        # SPAM DETECTION
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "spam"
        )

        if enabled:

            uid = message.author.id
            now = time.time()

            self.spam_cache[uid].append(now)

            while self.spam_cache[uid] and now - self.spam_cache[uid][0] > 5:
                self.spam_cache[uid].popleft()

            if len(self.spam_cache[uid]) >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Spam detected"
                )

                return

        # =========================
        # CAPS DETECTION
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "caps"
        )

        if enabled and len(content) >= 8:

            uppercase = sum(
                1 for c in message.content if c.isupper()
            )

            percentage = (
                uppercase / len(message.content)
            ) * 100

            if percentage >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Excessive caps"
                )

                return

        # =========================
        # INVITE DETECTION
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "invite"
        )

        if enabled:

            if re.search(INVITE_REGEX, content):

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Discord invite detected"
                )

                return

        # =========================
        # SCAM DETECTION
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "scam"
        )

        if enabled:

            for word in SCAM_WORDS:

                if word in content:

                    try:
                        await message.delete()
                    except:
                        pass

                    await self.execute_punishment(
                        message.author,
                        punishment,
                        "Scam message detected"
                    )

                    return

        # =========================
        # TOXICITY
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "toxicity"
        )

        if enabled:

            for word in TOXIC_WORDS:

                if word in content:

                    try:
                        await message.delete()
                    except:
                        pass

                    await self.execute_punishment(
                        message.author,
                        punishment,
                        "Toxic message"
                    )

                    return

        # =========================
        # DUPLICATE MESSAGES
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "duplicate"
        )

        if enabled:

            uid = message.author.id

            if (
                uid in self.last_message
                and self.last_message[uid] == content
            ):
                self.duplicate_cache[uid] += 1

            else:
                self.duplicate_cache[uid] = 1

            self.last_message[uid] = content

            if self.duplicate_cache[uid] >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Duplicate spam"
                )

                self.duplicate_cache[uid] = 0

                return

        # =========================
        # MENTION SPAM
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "mentions"
        )

        if enabled:

            if len(message.mentions) >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Mention spam"
                )

                return

        # =========================
        # LINK SPAM
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "linkspam"
        )

        if enabled:

            links = re.findall(LINK_REGEX, content)

            if len(links) >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Link spam"
                )

                return

        # =========================
        # EMOJI SPAM
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "emoji_spam"
        )

        if enabled:

            emoji_count = len(re.findall(EMOJI_REGEX, message.content))

            if emoji_count >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Emoji spam"
                )

                return

        # =========================
        # MEDIA ONLY
        # =========================

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "media"
        )

        if enabled:

            if "media-only" in message.channel.name:

                if (
                    not message.attachments
                    and "http" not in content
                ):

                    try:
                        await message.delete()
                    except:
                        pass

        # Save for ghost ping
        self.ghost_ping[message.id] = (
            message.author.id,
            [m.id for m in message.mentions]
        )

    # =========================
    # GHOST PING DETECTION
    # =========================

    @commands.Cog.listener()
    async def on_message_delete(self, message):

        if not message.guild:
            return

        enabled, limit, punishment = await self.get_feature(
            message.guild.id,
            "ghostping"
        )

        if not enabled:
            return

        if message.id not in self.ghost_ping:
            return

        author_id, mentions = self.ghost_ping[message.id]

        if mentions:

            embed = discord.Embed(
                title="👻 Ghost Ping Detected",
                color=discord.Color.red()
            )

            embed.description = (
                f"Author: <@{author_id}>\n"
                f"Mentions: {' '.join(f'<@{m}>' for m in mentions)}"
            )

            try:
                await message.channel.send(embed=embed)
            except:
                pass

    # =========================
    # RAID PROTECTION
    # =========================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        enabled, limit, punishment = await self.get_feature(
            member.guild.id,
            "raid"
        )

        if not enabled:
            return

        now = time.time()

        joins = self.join_cache[member.guild.id]

        joins.append(now)

        while joins and now - joins[0] > 10:
            joins.popleft()

        if len(joins) >= limit:

            try:

                if punishment == "kick":
                    await member.kick(reason="Raid protection")

                elif punishment == "ban":
                    await member.ban(reason="Raid protection")

            except:
                pass

    # =========================
    # ENABLE FEATURE
    # =========================

    @commands.hybrid_command(name="automod_enable")
    @commands.has_permissions(administrator=True)
    async def automod_enable(self, ctx, feature: str):

        if feature not in DEFAULTS:
            return await ctx.send("❌ Invalid feature")

        _, limit, punishment = await self.get_feature(
            ctx.guild.id,
            feature
        )

        await self.set_feature(
            ctx.guild.id,
            feature,
            1,
            limit,
            punishment
        )

        await ctx.send(f"✅ Enabled `{feature}`")

    # =========================
    # DISABLE FEATURE
    # =========================

    @commands.hybrid_command(name="automod_disable")
    @commands.has_permissions(administrator=True)
    async def automod_disable(self, ctx, feature: str):

        if feature not in DEFAULTS:
            return await ctx.send("❌ Invalid feature")

        _, limit, punishment = await self.get_feature(
            ctx.guild.id,
            feature
        )

        await self.set_feature(
            ctx.guild.id,
            feature,
            0,
            limit,
            punishment
        )

        await ctx.send(f"❌ Disabled `{feature}`")

    # =========================
    # AUTOMOD STATUS
    # =========================

    @commands.hybrid_command(name="automod_status")
    async def automod_status(self, ctx):

        embed = discord.Embed(
            title="🛡️ AutoMod Status",
            color=discord.Color.blurple()
        )

        for feature in DEFAULTS:

            enabled, limit, punishment = await self.get_feature(
                ctx.guild.id,
                feature
            )

            embed.add_field(
                name=feature,
                value=(
                    f"Enabled: {'✅' if enabled else '❌'}\n"
                    f"Limit: {limit}\n"
                    f"Punishment: {punishment}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

# =========================
# LOAD COG
# =========================

async def setup(bot):

    await bot.add_cog(
        AdvancedAutomod(bot)
    )
