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
# DEFAULT FEATURES
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
    "die",
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
    "bitcoin giveaway",
    "limited offer"
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

                await member.send(
                    f"⚠️ Warning in {member.guild.name}\n"
                    f"Reason: {reason}\n"
                    f"Warnings: {warns}"
                )

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

        if (
            not message.guild
            or message.author.bot
        ):
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

        if enabled:

            if len(content) >= 8:

                upper = sum(
                    1 for c in content
                    if c.isupper()
                )

                percent = (
                    upper / len(content)
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
        # DUPLICATES
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

        await self.bot.process_commands(message)

    # =========================
    # GHOST PING
    # =========================
    @commands.Cog.listener()
    async def on_message_delete(self, message):

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

            text = " ".join(
                f"<@{x}>"
                for x in mentions
            )

            embed = discord.Embed(
                title="👻 Ghost Ping",
                description=(
                    f"Author: <@{author_id}>\n"
                    f"Mentions: {text}"
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
    # ENABLE
    # =========================
    @commands.hybrid_command(
        name="automod_enable",
        help="Enable an automod feature.",
        extras={
            "example": "!automod_enable spam",
            "tips": "Enable protections individually."
        }
    )
    async def automod_enable(
        self,
        ctx,
        feature: str
    ):

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

        await ctx.send(
            f"✅ Enabled `{feature}`"
        )

    # =========================
    # DISABLE
    # =========================
    @commands.hybrid_command(
        name="automod_disable",
        help="Disable an automod feature.",
        extras={
            "example": "!automod_disable spam",
            "tips": "Disable protections individually."
        }
    )
    async def automod_disable(
        self,
        ctx,
        feature: str
    ):

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

        await ctx.send(
            f"❌ Disabled `{feature}`"
        )

    # =========================
    # LIMIT
    # =========================
    @commands.hybrid_command(
        name="automod_limit",
        help="Change automod limits.",
        extras={
            "example": "!automod_limit spam 10",
            "tips": "Higher values make automod less strict."
        }
    )
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

    # =========================
    # PUNISHMENT
    # =========================
    @commands.hybrid_command(
        name="automod_punishment",
        help="Change punishments.",
        extras={
            "example": "!automod_punishment spam timeout",
            "tips": "Use warn/timeout/kick/ban."
        }
    )
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

    # =========================
    # STATUS
    # =========================
    @commands.hybrid_command(
        name="automod_status",
        help="View automod settings.",
        extras={
            "example": "!automod_status",
            "tips": "Shows all automod systems."
        }
    )
    async def automod_status(self, ctx):

        embed = discord.Embed(
            title="🛡️ AutoMod Settings",
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

    # =========================
    # WARNINGS
    # =========================
    @commands.hybrid_command(
        name="warnings",
        help="View user warnings.",
        extras={
            "example": "!warnings @user",
            "tips": "Tracks user punishments."
        }
    )
    async def warnings(
        self,
        ctx,
        member: discord.Member
    ):

        warns = self.get_warns(
            ctx.guild.id,
            member.id
        )

        embed = discord.Embed(
            title="⚠️ Warnings",
            description=(
                f"{member.mention} has "
                f"`{warns}` warning(s)."
            ),
            color=discord.Color.orange()
        )

        await ctx.send(embed=embed)

    # =========================
    # VERIFY SETUP
    # =========================
    @commands.hybrid_command(
        name="setupverify",
        help="Setup verification system.",
        extras={
            "example": "!setupverify @Verified",
            "tips": "Users click a button to verify."
        }
    )
    async def setupverify(
        self,
        ctx,
        role: discord.Role
    ):

        cursor.execute(
            """
            DELETE FROM verification
            WHERE guild_id=?
            """,
            (ctx.guild.id,)
        )

        cursor.execute(
            """
            INSERT INTO verification
            VALUES (?, ?, ?)
            """,
            (
                ctx.guild.id,
                role.id,
                ctx.channel.id
            )
        )

        db.commit()

        embed = discord.Embed(
            title="✅ Verification",
            description="Click below to verify.",
            color=discord.Color.green()
        )

        await ctx.send(
            embed=embed,
            view=VerifyView()
        )

async def setup(bot):

    await bot.add_cog(
        AdvancedAutomod(bot)
    )
