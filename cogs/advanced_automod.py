import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import time
import re
from collections import defaultdict

# =========================
# DATABASE
# =========================
db = sqlite3.connect(
    "advanced_automod.db",
    check_same_thread=False
)

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS automod_settings(
    guild_id INTEGER,
    feature TEXT,
    enabled INTEGER,
    limit_value INTEGER,
    punishment TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings(
    guild_id INTEGER,
    user_id INTEGER,
    warns INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS whitelist(
    guild_id INTEGER,
    user_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS verification(
    guild_id INTEGER PRIMARY KEY,
    role_id INTEGER,
    channel_id INTEGER
)
""")

db.commit()

# =========================
# DEFAULTS
# =========================
DEFAULTS = {
    "spam": (1, 6, "timeout"),
    "caps": (1, 70, "warn"),
    "mentions": (1, 5, "timeout"),
    "duplicate": (1, 3, "timeout"),
    "invite": (1, 1, "timeout"),
    "scam": (1, 1, "ban"),
    "toxicity": (1, 1, "timeout"),
    "ghostping": (1, 1, "warn"),
    "raid": (1, 3, "kick"),
    "media": (0, 1, "warn")
}

# =========================
# DETECTION
# =========================
TOXIC_WORDS = [
    "kys",
    "kill yourself",
    "retard",
    "fatherless",
    "loser"
]

SCAM_WORDS = [
    "free nitro",
    "steam gift",
    "claim reward",
    "free robux",
    "bitcoin giveaway"
]

INVITE_REGEX = r"(discord\.gg\/|discord\.com\/invite\/)"

# =========================
# VERIFY VIEW
# =========================
class VerifyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.green,
        emoji="✅"
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        cursor.execute(
            """
            SELECT role_id
            FROM verification
            WHERE guild_id=?
            """,
            (interaction.guild.id,)
        )

        data = cursor.fetchone()

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

        await interaction.user.add_roles(role)

        await interaction.response.send_message(
            "✅ Verified successfully.",
            ephemeral=True
        )

# =========================
# COG
# =========================
class AdvancedAutomod(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.spam = defaultdict(list)
        self.last_message = {}
        self.duplicates = defaultdict(int)
        self.ghost_ping = {}

    # =========================
    # SETTINGS
    # =========================
    def get_feature(self, guild_id, feature):

        cursor.execute(
            """
            SELECT enabled, limit_value, punishment
            FROM automod_settings
            WHERE guild_id=? AND feature=?
            """,
            (guild_id, feature)
        )

        data = cursor.fetchone()

        if data:
            return data

        return DEFAULTS[feature]

    def set_feature(
        self,
        guild_id,
        feature,
        enabled,
        limit_value,
        punishment
    ):

        cursor.execute(
            """
            DELETE FROM automod_settings
            WHERE guild_id=? AND feature=?
            """,
            (guild_id, feature)
        )

        cursor.execute(
            """
            INSERT INTO automod_settings
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

        db.commit()

    # =========================
    # WHITELIST
    # =========================
    def is_whitelisted(
        self,
        guild_id,
        user_id
    ):

        cursor.execute(
            """
            SELECT *
            FROM whitelist
            WHERE guild_id=? AND user_id=?
            """,
            (guild_id, user_id)
        )

        return cursor.fetchone() is not None

    # =========================
    # WARN SYSTEM
    # =========================
    def get_warns(self, guild_id, user_id):

        cursor.execute(
            """
            SELECT warns
            FROM warnings
            WHERE guild_id=? AND user_id=?
            """,
            (guild_id, user_id)
        )

        data = cursor.fetchone()

        return data[0] if data else 0

    def add_warn(self, guild_id, user_id):

        warns = self.get_warns(
            guild_id,
            user_id
        ) + 1

        cursor.execute(
            """
            DELETE FROM warnings
            WHERE guild_id=? AND user_id=?
            """,
            (guild_id, user_id)
        )

        cursor.execute(
            """
            INSERT INTO warnings
            VALUES (?, ?, ?)
            """,
            (guild_id, user_id, warns)
        )

        db.commit()

        return warns

    # =========================
    # PUNISHMENT
    # =========================
    async def execute_punishment(
        self,
        member,
        punishment,
        reason
    ):

        try:

            if punishment == "warn":

                warns = self.add_warn(
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

                await member.kick(
                    reason=reason
                )

            elif punishment == "ban":

                await member.ban(
                    reason=reason
                )

        except:
            pass

    # =========================
    # MESSAGE EVENT
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):

        if not message.guild:
            return

        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)

        if ctx.valid:
            return

        if self.is_whitelisted(
            message.guild.id,
            message.author.id
        ):
            return

        content = message.content.lower()

        # =========================
        # SPAM
        # =========================
        enabled, limit, punishment = self.get_feature(
            message.guild.id,
            "spam"
        )

        if enabled:

            uid = message.author.id
            now = time.time()

            self.spam[uid].append(now)

            self.spam[uid] = [
                t for t in self.spam[uid]
                if now - t < 5
            ]

            if len(self.spam[uid]) >= limit:

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
        # CAPS
        # =========================
        enabled, limit, punishment = self.get_feature(
            message.guild.id,
            "caps"
        )

        if enabled and len(content) >= 8:

            upper = sum(
                1 for c in message.content
                if c.isupper()
            )

            percent = (
                upper / len(message.content)
            ) * 100

            if percent >= limit:

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
        # INVITES
        # =========================
        enabled, limit, punishment = self.get_feature(
            message.guild.id,
            "invite"
        )

        if enabled:

            if re.search(
                INVITE_REGEX,
                content
            ):

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Discord invite"
                )

                return

        # =========================
        # SCAM
        # =========================
        enabled, limit, punishment = self.get_feature(
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
                        "Scam detected"
                    )

                    return

        # =========================
        # TOXICITY
        # =========================
        enabled, limit, punishment = self.get_feature(
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
        # DUPLICATE
        # =========================
        enabled, limit, punishment = self.get_feature(
            message.guild.id,
            "duplicate"
        )

        if enabled:

            uid = message.author.id

            if (
                uid in self.last_message
                and self.last_message[uid] == content
            ):

                self.duplicates[uid] += 1

            else:

                self.duplicates[uid] = 1

            self.last_message[uid] = content

            if self.duplicates[uid] >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.execute_punishment(
                    message.author,
                    punishment,
                    "Duplicate spam"
                )

                self.duplicates[uid] = 0

                return

        # =========================
        # MENTION SPAM
        # =========================
        enabled, limit, punishment = self.get_feature(
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
        # MEDIA ONLY
        # =========================
        enabled, limit, punishment = self.get_feature(
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

        self.ghost_ping[message.id] = (
            message.author.id,
            [m.id for m in message.mentions]
        )

    # =========================
    # GHOSTPING
    # =========================
    @commands.Cog.listener()
    async def on_message_delete(self, message):

        if not message.guild:
            return

        enabled, limit, punishment = self.get_feature(
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
                description=(
                    f"Author: <@{author_id}>\n"
                    f"Mentions: {' '.join(f'<@{m}>' for m in mentions)}"
                ),
                color=discord.Color.red()
            )

            try:
                await message.channel.send(
                    embed=embed
                )
            except:
                pass

    # =========================
    # RAID PROTECTION
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):

        enabled, limit, punishment = self.get_feature(
            member.guild.id,
            "raid"
        )

        if not enabled:
            return

        age = (
            discord.utils.utcnow()
            - member.created_at
        ).days

        if age <= limit:

            try:

                if punishment == "kick":

                    await member.kick(
                        reason="Raid protection"
                    )

                elif punishment == "ban":

                    await member.ban(
                        reason="Raid protection"
                    )

            except:
                pass

    # =========================
    # COMMANDS
    # =========================
    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def automod_enable(self, ctx, feature: str):

        if feature not in DEFAULTS:
            return await ctx.send("❌ Invalid feature")

        _, limit, punishment = self.get_feature(
            ctx.guild.id,
            feature
        )

        self.set_feature(
            ctx.guild.id,
            feature,
            1,
            limit,
            punishment
        )

        await ctx.send(f"✅ Enabled `{feature}`")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def automod_disable(self, ctx, feature: str):

        if feature not in DEFAULTS:
            return await ctx.send("❌ Invalid feature")

        _, limit, punishment = self.get_feature(
            ctx.guild.id,
            feature
        )

        self.set_feature(
            ctx.guild.id,
            feature,
            0,
            limit,
            punishment
        )

        await ctx.send(f"❌ Disabled `{feature}`")

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def automod_limit(
        self,
        ctx,
        feature: str,
        limit: int
    ):

        if feature not in DEFAULTS:
            return await ctx.send("❌ Invalid feature")

        enabled, _, punishment = self.get_feature(
            ctx.guild.id,
            feature
        )

        self.set_feature(
            ctx.guild.id,
            feature,
            enabled,
            limit,
            punishment
        )

        await ctx.send(
            f"✅ `{feature}` limit set to `{limit}`"
        )

    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    async def automod_punishment(
        self,
        ctx,
        feature: str,
        punishment: str
    ):

        punishment = punishment.lower()

        if punishment not in [
            "warn",
            "timeout",
            "kick",
            "ban"
        ]:
            return await ctx.send(
                "❌ Invalid punishment"
            )

        enabled, limit, _ = self.get_feature(
            ctx.guild.id,
            feature
        )

        self.set_feature(
            ctx.guild.id,
            feature,
            enabled,
            limit,
            punishment
        )

        await ctx.send(
            f"✅ `{feature}` punishment set to `{punishment}`"
        )

    @commands.hybrid_command()
    async def automod_status(self, ctx):

        embed = discord.Embed(
            title="🛡️ AutoMod Status",
            color=discord.Color.blurple()
        )

        for feature in DEFAULTS:

            enabled, limit, punishment = self.get_feature(
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

async def setup(bot):

    await bot.add_cog(
        AdvancedAutomod(bot)
    )
