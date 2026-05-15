import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio
import time

from utils.dispatch import dispatch_log
from utils.config import (
    DB_PATH,
    BRAND_COLOR,
    ANTI_NUKE_LIMIT,
    WHITELIST
)

# =========================
# ANTINUKE SYSTEM
# =========================
class AntiNuke(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # {(guild_id, user_id, action): [timestamps]}
        self.cooldowns = {}

    # =========================
    # WHITELIST CHECK
    # =========================
    async def is_whitelisted(self, guild_id, user_id):

        if user_id in WHITELIST:
            return True

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
                SELECT 1 FROM antinuke_whitelist
                WHERE guild_id=? AND user_id=?
            """, (
                guild_id,
                user_id
            )) as cursor:

                return await cursor.fetchone() is not None

    # =========================
    # RATE LIMIT CHECK
    # =========================
    async def check_threshold(
        self,
        guild_id,
        user_id,
        action
    ):

        key = (guild_id, user_id, action)

        now = time.time()

        if key not in self.cooldowns:
            self.cooldowns[key] = []

        self.cooldowns[key].append(now)

        # Keep last 10 sec
        self.cooldowns[key] = [
            t for t in self.cooldowns[key]
            if now - t <= 10
        ]

        return len(self.cooldowns[key]) >= ANTI_NUKE_LIMIT

    # =========================
    # PUNISHMENT
    # =========================
    async def punish(
        self,
        guild,
        member,
        reason
    ):

        if not member:
            return

        if member.id == guild.owner_id:
            return

        try:

            await member.ban(
                reason=f"Dem Anti-Nuke | {reason}"
            )

            await dispatch_log(
                guild,
                "antinuke",
                content=(
                    f"🚨 **User Punished**\n\n"
                    f"**User:** {member.mention}\n"
                    f"**Reason:** {reason}"
                ),
                user_id=member.id
            )

        except Exception:

            try:

                await member.edit(
                    roles=[],
                    reason="Dem Anti-Nuke Emergency"
                )

            except:
                pass

    # =========================
    # CHANNEL DELETE
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        guild = channel.guild

        await asyncio.sleep(1)

        try:

            async for entry in guild.audit_logs(
                limit=1,
                action=discord.AuditLogAction.channel_delete
            ):

                user = entry.user

                if user.bot:
                    return

                if await self.is_whitelisted(
                    guild.id,
                    user.id
                ):
                    return

                triggered = await self.check_threshold(
                    guild.id,
                    user.id,
                    "channel_delete"
                )

                if not triggered:
                    return

                # =========================
                # RECOVER CHANNEL
                # =========================
                try:

                    restored = await channel.clone(
                        reason="Dem Anti-Nuke Recovery"
                    )

                    await restored.edit(
                        position=channel.position
                    )

                    await restored.send(
                        embed=discord.Embed(
                            title="🛡️ Channel Restored",
                            description=(
                                "This channel was automatically restored "
                                "by Dem Anti-Nuke."
                            ),
                            color=discord.Color.orange()
                        )
                    )

                except:
                    pass

                # =========================
                # PUNISH USER
                # =========================
                await self.punish(
                    guild,
                    user,
                    "Mass Channel Deletion"
                )

        except Exception as e:
            print(f"[ANTINUKE CHANNEL ERROR] {e}")

    # =========================
    # ROLE DELETE
    # =========================
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):

        guild = role.guild

        await asyncio.sleep(1)

        try:

            async for entry in guild.audit_logs(
                limit=1,
                action=discord.AuditLogAction.role_delete
            ):

                user = entry.user

                if user.bot:
                    return

                if await self.is_whitelisted(
                    guild.id,
                    user.id
                ):
                    return

                triggered = await self.check_threshold(
                    guild.id,
                    user.id,
                    "role_delete"
                )

                if not triggered:
                    return

                await self.punish(
                    guild,
                    user,
                    "Mass Role Deletion"
                )

        except Exception as e:
            print(f"[ANTINUKE ROLE ERROR] {e}")

    # =========================
    # BOT ADD PROTECTION
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):

        if not member.bot:
            return

        guild = member.guild

        await asyncio.sleep(1)

        try:

            async for entry in guild.audit_logs(
                limit=1,
                action=discord.AuditLogAction.bot_add
            ):

                user = entry.user

                if await self.is_whitelisted(
                    guild.id,
                    user.id
                ):
                    return

                # Ban added bot
                try:

                    await member.ban(
                        reason="Unauthorized Bot Added"
                    )

                except:
                    pass

                # Punish adder
                await self.punish(
                    guild,
                    user,
                    "Unauthorized Bot Addition"
                )

                await dispatch_log(
                    guild,
                    "antinuke",
                    content=(
                        f"🤖 **Unauthorized Bot Blocked**\n\n"
                        f"**Bot:** {member.mention}\n"
                        f"**Added By:** {user.mention}"
                    )
                )

        except Exception as e:
            print(f"[ANTINUKE BOT ERROR] {e}")

    # =========================
    # MASS ROLE CREATE
    # =========================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):

        guild = role.guild

        await asyncio.sleep(1)

        try:

            async for entry in guild.audit_logs(
                limit=1,
                action=discord.AuditLogAction.role_create
            ):

                user = entry.user

                if user.bot:
                    return

                if await self.is_whitelisted(
                    guild.id,
                    user.id
                ):
                    return

                triggered = await self.check_threshold(
                    guild.id,
                    user.id,
                    "role_create"
                )

                if triggered:

                    await role.delete(
                        reason="Dem Anti-Nuke Protection"
                    )

                    await self.punish(
                        guild,
                        user,
                        "Mass Role Creation"
                    )

        except Exception as e:
            print(f"[ANTINUKE CREATE ERROR] {e}")

    # =========================
    # ANTINUKE GROUP
    # =========================
    @commands.hybrid_group(
        name="antinuke",
        description="Manage Dem Anti-Nuke system."
    )
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx):

        if ctx.invoked_subcommand is None:

            embed = discord.Embed(
                title="🛡️ Anti-Nuke System",
                description=(
                    "Use the commands below to configure "
                    "Dem Anti-Nuke."
                ),
                color=BRAND_COLOR
            )

            embed.add_field(
                name="Commands",
                value=(
                    "`antinuke whitelist`\n"
                    "`antinuke unwhitelist`\n"
                    "`antinuke list`"
                ),
                inline=False
            )

            await ctx.send(embed=embed)

    # =========================
    # WHITELIST
    # =========================
    @antinuke.command(
        name="whitelist",
        description="Whitelist a user from Anti-Nuke."
    )
    async def whitelist(
        self,
        ctx,
        user: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                INSERT OR REPLACE INTO antinuke_whitelist
                (guild_id, user_id)
                VALUES (?, ?)
            """, (
                ctx.guild.id,
                user.id
            ))

            await db.commit()

        embed = discord.Embed(
            description=(
                f"✅ {user.mention} is now "
                f"whitelisted from Anti-Nuke."
            ),
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    # =========================
    # UNWHITELIST
    # =========================
    @antinuke.command(
        name="unwhitelist",
        description="Remove a user from whitelist."
    )
    async def unwhitelist(
        self,
        ctx,
        user: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                DELETE FROM antinuke_whitelist
                WHERE guild_id=? AND user_id=?
            """, (
                ctx.guild.id,
                user.id
            ))

            await db.commit()

        embed = discord.Embed(
            description=(
                f"✅ Removed {user.mention} "
                f"from Anti-Nuke whitelist."
            ),
            color=discord.Color.orange()
        )

        await ctx.send(embed=embed)

    # =========================
    # LIST WHITELIST
    # =========================
    @antinuke.command(
        name="list",
        description="View Anti-Nuke whitelist."
    )
    async def whitelist_list(self, ctx):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
                SELECT user_id FROM antinuke_whitelist
                WHERE guild_id=?
            """, (
                ctx.guild.id,
            )) as cursor:

                data = await cursor.fetchall()

        if not data:

            return await ctx.send(
                embed=discord.Embed(
                    description="❌ No users are whitelisted.",
                    color=discord.Color.red()
                )
            )

        users = []

        for row in data:
            users.append(f"<@{row[0]}>")

        embed = discord.Embed(
            title="🛡️ Anti-Nuke Whitelist",
            description="\n".join(users),
            color=BRAND_COLOR
        )

        await ctx.send(embed=embed)


# =========================
# LOAD COG
# =========================
async def setup(bot):

    await bot.add_cog(AntiNuke(bot))
