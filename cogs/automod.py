import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import time
from collections import defaultdict

# =========================
# DATABASE
# =========================
db = sqlite3.connect(
    "automod.db",
    check_same_thread=False
)

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS automod_settings(
    guild_id INTEGER,
    feature TEXT,
    value TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS automod_whitelist(
    guild_id INTEGER,
    user_id INTEGER
)
""")

db.commit()

# =========================
# DEFAULTS
# =========================
DEFAULTS = {
    "spam_enabled": "true",
    "spam_limit": "6",

    "caps_enabled": "true",
    "caps_limit": "70",

    "mention_enabled": "true",
    "mention_limit": "5",

    "duplicate_enabled": "true",
    "duplicate_limit": "3",

    "invite_enabled": "true",

    "punishment": "timeout"
}

# =========================
# COG
# =========================
class AutoMod(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.spam = defaultdict(list)
        self.duplicates = defaultdict(int)
        self.last_message = {}

    # =========================
    # SETTINGS
    # =========================
    def get_setting(
        self,
        guild_id,
        feature
    ):

        cursor.execute(
            """
            SELECT value
            FROM automod_settings
            WHERE guild_id=? AND feature=?
            """,
            (guild_id, feature)
        )

        data = cursor.fetchone()

        if data:
            return data[0]

        return DEFAULTS.get(feature)

    def set_setting(
        self,
        guild_id,
        feature,
        value
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
            VALUES (?, ?, ?)
            """,
            (
                guild_id,
                feature,
                str(value)
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
            FROM automod_whitelist
            WHERE guild_id=? AND user_id=?
            """,
            (guild_id, user_id)
        )

        return cursor.fetchone() is not None

    # =========================
    # PUNISH
    # =========================
    async def punish(
        self,
        member,
        reason
    ):

        punishment = self.get_setting(
            member.guild.id,
            "punishment"
        )

        try:

            if punishment == "warn":

                await member.send(
                    f"⚠️ Warning in {member.guild.name}\nReason: {reason}"
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

        content = message.content

        # =========================
        # SPAM
        # =========================
        if self.get_setting(
            message.guild.id,
            "spam_enabled"
        ) == "true":

            limit = int(
                self.get_setting(
                    message.guild.id,
                    "spam_limit"
                )
            )

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

                await self.punish(
                    message.author,
                    "Spam detected"
                )

                return

        # =========================
        # CAPS
        # =========================
        if self.get_setting(
            message.guild.id,
            "caps_enabled"
        ) == "true":

            if len(content) >= 8:

                upper = sum(
                    1 for c in content
                    if c.isupper()
                )

                percent = (
                    upper / len(content)
                ) * 100

                limit = int(
                    self.get_setting(
                        message.guild.id,
                        "caps_limit"
                    )
                )

                if percent >= limit:

                    try:
                        await message.delete()
                    except:
                        pass

                    await self.punish(
                        message.author,
                        "Excessive caps"
                    )

                    return

        # =========================
        # MENTION SPAM
        # =========================
        if self.get_setting(
            message.guild.id,
            "mention_enabled"
        ) == "true":

            limit = int(
                self.get_setting(
                    message.guild.id,
                    "mention_limit"
                )
            )

            if len(message.mentions) >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.punish(
                    message.author,
                    "Mention spam"
                )

                return

        # =========================
        # DUPLICATE
        # =========================
        if self.get_setting(
            message.guild.id,
            "duplicate_enabled"
        ) == "true":

            uid = message.author.id

            if (
                uid in self.last_message
                and self.last_message[uid] == content
            ):

                self.duplicates[uid] += 1

            else:

                self.duplicates[uid] = 1

            self.last_message[uid] = content

            limit = int(
                self.get_setting(
                    message.guild.id,
                    "duplicate_limit"
                )
            )

            if self.duplicates[uid] >= limit:

                try:
                    await message.delete()
                except:
                    pass

                await self.punish(
                    message.author,
                    "Duplicate spam"
                )

                self.duplicates[uid] = 0

                return

        # =========================
        # INVITES
        # =========================
        if self.get_setting(
            message.guild.id,
            "invite_enabled"
        ) == "true":

            text = content.lower()

            if (
                "discord.gg/"
                in text
                or "discord.com/invite/"
                in text
            ):

                try:
                    await message.delete()
                except:
                    pass

                await self.punish(
                    message.author,
                    "Server invite"
                )

                return

        await self.bot.process_commands(message)

    # =========================
    # ENABLE
    # =========================
    @commands.hybrid_command(
        name="automod_enable"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def automod_enable(
        self,
        ctx,
        feature: str
    ):

        self.set_setting(
            ctx.guild.id,
            f"{feature}_enabled",
            "true"
        )

        await ctx.send(
            f"✅ Enabled `{feature}`"
        )

    # =========================
    # DISABLE
    # =========================
    @commands.hybrid_command(
        name="automod_disable"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def automod_disable(
        self,
        ctx,
        feature: str
    ):

        self.set_setting(
            ctx.guild.id,
            f"{feature}_enabled",
            "false"
        )

        await ctx.send(
            f"❌ Disabled `{feature}`"
        )

    # =========================
    # LIMIT
    # =========================
    @commands.hybrid_command(
        name="automod_limit"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def automod_limit(
        self,
        ctx,
        feature: str,
        limit: int
    ):

        self.set_setting(
            ctx.guild.id,
            f"{feature}_limit",
            limit
        )

        await ctx.send(
            f"✅ {feature} limit set to `{limit}`"
        )

    # =========================
    # PUNISHMENT
    # =========================
    @commands.hybrid_command(
        name="automod_punishment"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def automod_punishment(
        self,
        ctx,
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
                "❌ Use: warn / timeout / kick / ban"
            )

        self.set_setting(
            ctx.guild.id,
            "punishment",
            punishment
        )

        await ctx.send(
            f"✅ Punishment set to `{punishment}`"
        )

    # =========================
    # WHITELIST ADD
    # =========================
    @commands.hybrid_command(
        name="automod_whitelist_add"
    )
    async def automod_whitelist_add(
        self,
        ctx,
        member: discord.Member
    ):

        cursor.execute(
            """
            INSERT INTO automod_whitelist
            VALUES (?, ?)
            """,
            (
                ctx.guild.id,
                member.id
            )
        )

        db.commit()

        await ctx.send(
            f"✅ {member.mention} whitelisted"
        )

    # =========================
    # WHITELIST REMOVE
    # =========================
    @commands.hybrid_command(
        name="automod_whitelist_remove"
    )
    async def automod_whitelist_remove(
        self,
        ctx,
        member: discord.Member
    ):

        cursor.execute(
            """
            DELETE FROM automod_whitelist
            WHERE guild_id=? AND user_id=?
            """,
            (
                ctx.guild.id,
                member.id
            )
        )

        db.commit()

        await ctx.send(
            f"❌ Removed {member.mention}"
        )

    # =========================
    # STATUS
    # =========================
    @commands.hybrid_command(
        name="automod_status"
    )
    async def automod_status(
        self,
        ctx
    ):

        embed = discord.Embed(
            title="🛡️ AutoMod Settings",
            color=discord.Color.blurple()
        )

        for key in DEFAULTS:

            value = self.get_setting(
                ctx.guild.id,
                key
            )

            embed.add_field(
                name=key,
                value=value,
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):

    await bot.add_cog(
        AutoMod(bot)
    )
