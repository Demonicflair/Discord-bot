import math
import time
import random
import asyncio
import datetime
import discord
import aiosqlite

from discord.ext import commands, tasks
from discord import app_commands

from utils.config import (
    DB_PATH,
    BRAND_COLOR,
    LEVEL_ROLES,
    XP_PER_MESSAGE
)

# =========================================
# LEVELING SYSTEM V2
# Arcane + Greed Inspired
# =========================================

LEVEL_UP_COLOR = 0xf1c40f

VOICE_REWARD_TIME = 60
MESSAGE_COOLDOWN = 10

PRESTIGE_LEVEL = 100

# =========================================
# LEVELING COG
# =========================================

class Leveling(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.message_cooldowns = {}

        self.voice_tracking = {}

        self.voice_xp.start()

    # =========================================
    # DATABASE INIT
    # =========================================

    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            # Main Level Table
            await db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                guild_id INTEGER,
                user_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                prestige INTEGER DEFAULT 0,
                messages INTEGER DEFAULT 0,
                voice_seconds INTEGER DEFAULT 0,
                weekly_xp INTEGER DEFAULT 0,
                rep INTEGER DEFAULT 0,
                bio TEXT DEFAULT '',
                PRIMARY KEY(guild_id, user_id)
            )
            """)

            # Settings
            await db.execute("""
            CREATE TABLE IF NOT EXISTS level_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                levelup_channel INTEGER,
                announce INTEGER DEFAULT 1
            )
            """)

            # Blacklisted Channels
            await db.execute("""
            CREATE TABLE IF NOT EXISTS level_blacklist (
                guild_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY(guild_id, channel_id)
            )
            """)

            # XP Boosters
            await db.execute("""
            CREATE TABLE IF NOT EXISTS xp_boosts (
                guild_id INTEGER,
                role_id INTEGER,
                multiplier REAL DEFAULT 1.0,
                PRIMARY KEY(guild_id, role_id)
            )
            """)

            await db.commit()

    # =========================================
    # XP FORMULA
    # =========================================

    def calculate_level(self, xp):

        return int(0.2 * math.sqrt(xp))

    def xp_needed(self, level):

        return int((level / 0.2) ** 2)

    # =========================================
    # GET DATA
    # =========================================

    async def get_data(
        self,
        guild_id,
        user_id
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
            SELECT
            xp,
            level,
            prestige,
            messages,
            voice_seconds,
            weekly_xp,
            rep,
            bio
            FROM levels
            WHERE guild_id=? AND user_id=?
            """, (
                guild_id,
                user_id
            )) as cursor:

                data = await cursor.fetchone()

                if data:
                    return data

            await db.execute("""
            INSERT INTO levels
            (guild_id, user_id)
            VALUES (?, ?)
            """, (
                guild_id,
                user_id
            ))

            await db.commit()

        return (
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            ""
        )

    # =========================================
    # XP BOOSTERS
    # =========================================

    async def get_multiplier(
        self,
        member
    ):

        multiplier = 1.0

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
            SELECT role_id, multiplier
            FROM xp_boosts
            WHERE guild_id=?
            """, (
                member.guild.id,
            )) as cursor:

                boosts = await cursor.fetchall()

        for role_id, multi in boosts:

            role = member.guild.get_role(role_id)

            if role and role in member.roles:

                multiplier += multi

        return multiplier

    # =========================================
    # ADD XP
    # =========================================

    async def add_xp(
        self,
        member,
        amount
    ):

        data = await self.get_data(
            member.guild.id,
            member.id
        )

        xp, level, prestige, messages, voice_seconds, weekly_xp, rep, bio = data

        multiplier = await self.get_multiplier(member)

        amount = int(amount * multiplier)

        xp += amount
        weekly_xp += amount

        new_level = self.calculate_level(xp)

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            UPDATE levels
            SET xp=?,
                level=?,
                weekly_xp=?
            WHERE guild_id=? AND user_id=?
            """, (
                xp,
                new_level,
                weekly_xp,
                member.guild.id,
                member.id
            ))

            await db.commit()

        # =========================================
        # LEVEL UP
        # =========================================

        if new_level > level:

            await self.level_up(
                member,
                new_level
            )

    # =========================================
    # LEVEL UP EVENT
    # =========================================

    async def level_up(
        self,
        member,
        level
    ):

        embed = discord.Embed(
            title="🎉 Level Up!",
            description=(
                f"{member.mention} reached "
                f"**Level {level}**"
            ),
            color=LEVEL_UP_COLOR
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="✨ Rewards",
            value="Keep chatting to earn more XP!",
            inline=False
        )

        try:

            await member.send(
                embed=embed
            )

        except:
            pass

        # =========================================
        # AUTO ROLE REWARDS
        # =========================================

        for req_level, role_name in LEVEL_ROLES.items():

            if level >= req_level:

                role = discord.utils.get(
                    member.guild.roles,
                    name=role_name
                )

                if role:

                    try:
                        await member.add_roles(
                            role,
                            reason="Level Reward"
                        )
                    except:
                        pass

        # =========================================
        # PRESTIGE
        # =========================================

        if level >= PRESTIGE_LEVEL:

            async with aiosqlite.connect(DB_PATH) as db:

                await db.execute("""
                UPDATE levels
                SET prestige = prestige + 1,
                    xp = 0,
                    level = 0
                WHERE guild_id=? AND user_id=?
                """, (
                    member.guild.id,
                    member.id
                ))

                await db.commit()

            try:

                await member.send(
                    "🏆 You prestiged and restarted at Level 0!"
                )

            except:
                pass

    # =========================================
    # MESSAGE XP
    # =========================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message
    ):

        if not message.guild:
            return

        if message.author.bot:
            return

        key = (
            message.guild.id,
            message.author.id
        )

        now = time.time()

        # Cooldown
        if key in self.message_cooldowns:

            if now - self.message_cooldowns[key] < MESSAGE_COOLDOWN:
                return

        self.message_cooldowns[key] = now

        # Blacklisted Channels
        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
            SELECT 1
            FROM level_blacklist
            WHERE guild_id=? AND channel_id=?
            """, (
                message.guild.id,
                message.channel.id
            )) as cursor:

                blocked = await cursor.fetchone()

        if blocked:
            return

        # Anti Spam
        if len(message.content) < 4:
            return

        xp_gain = random.randint(
            XP_PER_MESSAGE - 5,
            XP_PER_MESSAGE + 10
        )

        await self.add_xp(
            message.author,
            xp_gain
        )

        # Messages
        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            UPDATE levels
            SET messages = messages + 1
            WHERE guild_id=? AND user_id=?
            """, (
                message.guild.id,
                message.author.id
            ))

            await db.commit()

    # =========================================
    # VOICE XP
    # =========================================

    @tasks.loop(minutes=1)
    async def voice_xp(self):

        for guild in self.bot.guilds:

            for vc in guild.voice_channels:

                for member in vc.members:

                    if member.bot:
                        continue

                    await self.add_xp(
                        member,
                        20
                    )

                    async with aiosqlite.connect(DB_PATH) as db:

                        await db.execute("""
                        UPDATE levels
                        SET voice_seconds = voice_seconds + ?
                        WHERE guild_id=? AND user_id=?
                        """, (
                            VOICE_REWARD_TIME,
                            guild.id,
                            member.id
                        ))

                        await db.commit()

    # =========================================
    # RANK
    # =========================================

    @commands.hybrid_command(
        name="rank",
        description="View your rank profile."
    )
    async def rank(
        self,
        ctx,
        member: discord.Member = None
    ):

        member = member or ctx.author

        data = await self.get_data(
            ctx.guild.id,
            member.id
        )

        xp, level, prestige, messages, voice_seconds, weekly_xp, rep, bio = data

        next_xp = self.xp_needed(level + 1)

        progress = round(
            (xp / next_xp) * 100,
            1
        )

        embed = discord.Embed(
            title=f"📈 {member.name}'s Profile",
            color=BRAND_COLOR
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="🏆 Level",
            value=f"`{level}`"
        )

        embed.add_field(
            name="⭐ XP",
            value=f"`{xp}` / `{next_xp}`"
        )

        embed.add_field(
            name="🌟 Prestige",
            value=f"`{prestige}`"
        )

        embed.add_field(
            name="💬 Messages",
            value=f"`{messages}`"
        )

        embed.add_field(
            name="🎤 Voice Time",
            value=f"`{voice_seconds // 60}m`"
        )

        embed.add_field(
            name="🤝 Reputation",
            value=f"`{rep}`"
        )

        embed.add_field(
            name="📊 Progress",
            value=f"`{progress}%`",
            inline=False
        )

        if bio:

            embed.add_field(
                name="📝 Bio",
                value=bio[:300],
                inline=False
            )

        embed.set_footer(
            text="Dem Advanced Leveling"
        )

        await ctx.send(embed=embed)

    # =========================================
    # LEADERBOARD
    # =========================================

    @commands.hybrid_command(
        name="leaderboard",
        aliases=["lb"],
        description="View the XP leaderboard."
    )
    async def leaderboard(
        self,
        ctx
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
            SELECT user_id, level, xp
            FROM levels
            WHERE guild_id=?
            ORDER BY xp DESC
            LIMIT 10
            """, (
                ctx.guild.id,
            )) as cursor:

                data = await cursor.fetchall()

        embed = discord.Embed(
            title="🏆 XP Leaderboard",
            color=discord.Color.gold()
        )

        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]

        desc = ""

        for i, (
            user_id,
            level,
            xp
        ) in enumerate(data, start=1):

            member = ctx.guild.get_member(user_id)

            if not member:
                continue

            medal = medals[i - 1] if i <= 3 else f"`#{i}`"

            desc += (
                f"{medal} {member.mention} • "
                f"Level `{level}` • `{xp} XP`\n"
            )

        embed.description = desc

        await ctx.send(embed=embed)

    # =========================================
    # WEEKLY LEADERBOARD
    # =========================================

    @commands.hybrid_command(
        name="weeklylb",
        description="Weekly XP leaderboard."
    )
    async def weeklylb(
        self,
        ctx
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
            SELECT user_id, weekly_xp
            FROM levels
            WHERE guild_id=?
            ORDER BY weekly_xp DESC
            LIMIT 10
            """, (
                ctx.guild.id,
            )) as cursor:

                data = await cursor.fetchall()

        embed = discord.Embed(
            title="📅 Weekly Leaderboard",
            color=discord.Color.blurple()
        )

        text = ""

        for i, (
            user_id,
            xp
        ) in enumerate(data, start=1):

            member = ctx.guild.get_member(user_id)

            if not member:
                continue

            text += (
                f"`#{i}` {member.mention} • `{xp} XP`\n"
            )

        embed.description = text

        await ctx.send(embed=embed)

    # =========================================
    # REP SYSTEM
    # =========================================

    @commands.hybrid_command(
        name="rep",
        description="Give reputation to someone."
    )
    async def rep(
        self,
        ctx,
        member: discord.Member
    ):

        if member == ctx.author:

            return await ctx.send(
                "❌ You cannot rep yourself."
            )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            UPDATE levels
            SET rep = rep + 1
            WHERE guild_id=? AND user_id=?
            """, (
                ctx.guild.id,
                member.id
            ))

            await db.commit()

        await ctx.send(
            f"🤝 {ctx.author.mention} gave rep to {member.mention}"
        )

    # =========================================
    # BIO
    # =========================================

    @commands.hybrid_command(
        name="setbio",
        description="Set your profile bio."
    )
    async def setbio(
        self,
        ctx,
        *,
        text: str
    ):

        if len(text) > 300:

            return await ctx.send(
                "❌ Bio too long."
            )

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            UPDATE levels
            SET bio=?
            WHERE guild_id=? AND user_id=?
            """, (
                text,
                ctx.guild.id,
                ctx.author.id
            ))

            await db.commit()

        await ctx.send(
            "✅ Updated your bio."
        )

    # =========================================
    # BLACKLIST CHANNEL
    # =========================================

    @commands.hybrid_command(
        name="levelblacklist",
        description="Blacklist a channel from XP."
    )
    @commands.has_permissions(
        administrator=True
    )
    async def levelblacklist(
        self,
        ctx,
        channel: discord.TextChannel
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            INSERT OR REPLACE INTO level_blacklist
            VALUES (?, ?)
            """, (
                ctx.guild.id,
                channel.id
            ))

            await db.commit()

        await ctx.send(
            f"🚫 {channel.mention} removed from leveling."
        )

    # =========================================
    # XP BOOST
    # =========================================

    @commands.hybrid_command(
        name="xpboost",
        description="Add XP boost to a role."
    )
    @commands.has_permissions(
        administrator=True
    )
    async def xpboost(
        self,
        ctx,
        role: discord.Role,
        multiplier: float
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            INSERT OR REPLACE INTO xp_boosts
            VALUES (?, ?, ?)
            """, (
                ctx.guild.id,
                role.id,
                multiplier
            ))

            await db.commit()

        await ctx.send(
            f"✨ {role.mention} now gets `{multiplier}x` XP boost."
        )


# =========================================
# LOAD COG
# =========================================

async def setup(bot):

    await bot.add_cog(
        Leveling(bot)
    )
