import asyncio
import time
import aiosqlite
import discord

from collections import defaultdict
from discord.ext import commands
from discord import app_commands

from utils.dispatch import dispatch_log
from utils.embeds import (
    success_embed,
    error_embed,
    warning_embed,
    base_embed
)
from utils.checks import is_owner_or_admin
from utils.config import (
    DB_PATH,
    BRAND_COLOR,
    ANTI_NUKE_LIMIT,
    WHITELIST
)

# =========================
# ANTINUKE
# =========================

class AntiNuke(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # {(guild_id, user_id, action): [timestamps]}
        self.cooldowns = defaultdict(list)

    # =========================
    # DATABASE SETUP
    # =========================

    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
            CREATE TABLE IF NOT EXISTS antinuke_whitelist(
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY(guild_id, user_id)
            )
            """)

            await db.commit()

    # =========================
    # WHITELIST CHECK
    # =========================

    async def is_whitelisted(
        self,
        guild_id: int,
        user_id: int
    ):

        if user_id in WHITELIST:
            return True

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
                SELECT 1
                FROM antinuke_whitelist
                WHERE guild_id = ?
                AND user_id = ?
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
        guild_id: int,
        user_id: int,
        action: str
    ):

        key = (guild_id, user_id, action)

        now = time.time()

        self.cooldowns[key].append(now)

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
        guild: discord.Guild,
        member: discord.Member,
        reason: str
    ):

        if not member:
            return

        if member.id == guild.owner_id:
            return

        if member.top_role >= guild.me.top_role:
            return

        try:

            await member.ban(
                reason=f"Dem Anti-Nuke | {reason}",
                delete_message_days=1
            )

            await dispatch_log(
                guild=guild,
                log_type="antinuke",
                content=(
                    f"🚨 **Anti-Nuke Triggered**\n\n"
                    f"**User:** {member} ({member.id})\n"
                    f"**Action:** {reason}\n"
                    f"**Punishment:** Ban"
                ),
                user_id=member.id
            )

        except Exception:

            try:

                await member.edit(
                    roles=[],
                    reason="Dem Anti-Nuke Emergency Lockdown"
                )

            except:
                pass

    # =========================
    # AUDIT LOG FETCH
    # =========================

    async def fetch_entry(
        self,
        guild: discord.Guild,
        action
    ):

        await asyncio.sleep(1)

        async for entry in guild.audit_logs(
            limit=1,
            action=action
        ):

            return entry

    # =========================
    # CHANNEL DELETE
    # =========================

    @commands.Cog.listener()
    async def on_guild_channel_delete(
        self,
        channel
    ):

        guild = channel.guild

        try:

            entry = await self.fetch_entry(
                guild,
                discord.AuditLogAction.channel_delete
            )

            if not entry:
                return

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
            # RESTORE CHANNEL
            # =========================

            try:

                restored = await channel.clone(
                    reason="Dem Anti-Nuke Recovery"
                )

                await restored.edit(
                    position=channel.position
                )

                await restored.send(
                    embed=warning_embed(
                        "🛡️ Channel automatically restored by Anti-Nuke."
                    )
                )

            except:
                pass

            await self.punish(
                guild,
                user,
                "Mass Channel Deletion"
            )

        except Exception as e:
            print(f"[ANTINUKE CHANNEL DELETE] {e}")

    # =========================
    # CHANNEL CREATE
    # =========================

    @commands.Cog.listener()
    async def on_guild_channel_create(
        self,
        channel
    ):

        guild = channel.guild

        try:

            entry = await self.fetch_entry(
                guild,
                discord.AuditLogAction.channel_create
            )

            if not entry:
                return

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
                "channel_create"
            )

            if not triggered:
                return

            try:
                await channel.delete(
                    reason="Dem Anti-Nuke Protection"
                )
            except:
                pass

            await self.punish(
                guild,
                user,
                "Mass Channel Creation"
            )

        except Exception as e:
            print(f"[ANTINUKE CHANNEL CREATE] {e}")

    # =========================
    # ROLE DELETE
    # =========================

    @commands.Cog.listener()
    async def on_guild_role_delete(
        self,
        role
    ):

        guild = role.guild

        try:

            entry = await self.fetch_entry(
                guild,
                discord.AuditLogAction.role_delete
            )

            if not entry:
                return

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
            print(f"[ANTINUKE ROLE DELETE] {e}")

    # =========================
    # ROLE CREATE
    # =========================

    @commands.Cog.listener()
    async def on_guild_role_create(
        self,
        role
    ):

        guild = role.guild

        try:

            entry = await self.fetch_entry(
                guild,
                discord.AuditLogAction.role_create
            )

            if not entry:
                return

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

            if not triggered:
                return

            try:
                await role.delete(
                    reason="Dem Anti-Nuke Protection"
                )
            except:
                pass

            await self.punish(
                guild,
                user,
                "Mass Role Creation"
            )

        except Exception as e:
            print(f"[ANTINUKE ROLE CREATE] {e}")

    # =========================
    # BOT ADD
    # =========================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member
    ):

        if not member.bot:
            return

        guild = member.guild

        try:

            entry = await self.fetch_entry(
                guild,
                discord.AuditLogAction.bot_add
            )

            if not entry:
                return

            user = entry.user

            if await self.is_whitelisted(
                guild.id,
                user.id
            ):
                return

            try:

                await member.ban(
                    reason="Unauthorized Bot Added"
                )

            except:
                pass

            await self.punish(
                guild,
                user,
                "Unauthorized Bot Addition"
            )

            await dispatch_log(
                guild=guild,
                log_type="antinuke",
                content=(
                    f"🤖 **Unauthorized Bot Blocked**\n\n"
                    f"**Bot:** {member} ({member.id})\n"
                    f"**Added By:** {user} ({user.id})"
                ),
                user_id=user.id
            )

        except Exception as e:
            print(f"[ANTINUKE BOT ADD] {e}")

    # =========================
    # WEBHOOK CREATE
    # =========================

    @commands.Cog.listener()
    async def on_webhooks_update(
        self,
        channel
    ):

        guild = channel.guild

        try:

            entry = await self.fetch_entry(
                guild,
                discord.AuditLogAction.webhook_create
            )

            if not entry:
                return

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
                "webhook_create"
            )

            if not triggered:
                return

            webhooks = await channel.webhooks()

            for webhook in webhooks:

                try:
                    await webhook.delete()
                except:
                    pass

            await self.punish(
                guild,
                user,
                "Mass Webhook Creation"
            )

        except Exception as e:
            print(f"[ANTINUKE WEBHOOK] {e}")

    # =========================
    # GROUP
    # =========================

    @commands.hybrid_group(
        name="antinuke",
        description="Manage Dem Anti-Nuke."
    )
    @commands.check(is_owner_or_admin)
    async def antinuke(self, ctx):

        if ctx.invoked_subcommand is None:

            embed = base_embed(
                title="🛡️ Dem Anti-Nuke",
                description=(
                    "Advanced server protection system.\n\n"
                    "`/antinuke whitelist`\n"
                    "`/antinuke unwhitelist`\n"
                    "`/antinuke list`"
                )
            )

            await ctx.send(embed=embed)

    # =========================
    # WHITELIST
    # =========================

    @antinuke.command(
        name="whitelist"
    )
    async def whitelist(
        self,
        ctx,
        user: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                INSERT OR REPLACE INTO antinuke_whitelist
                (
                    guild_id,
                    user_id
                )
                VALUES (?, ?)
            """, (
                ctx.guild.id,
                user.id
            ))

            await db.commit()

        await ctx.send(
            embed=success_embed(
                f"{user.mention} added to Anti-Nuke whitelist."
            )
        )

    # =========================
    # UNWHITELIST
    # =========================

    @antinuke.command(
        name="unwhitelist"
    )
    async def unwhitelist(
        self,
        ctx,
        user: discord.Member
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                DELETE FROM antinuke_whitelist
                WHERE guild_id = ?
                AND user_id = ?
            """, (
                ctx.guild.id,
                user.id
            ))

            await db.commit()

        await ctx.send(
            embed=success_embed(
                f"{user.mention} removed from whitelist."
            )
        )

    # =========================
    # LIST
    # =========================

    @antinuke.command(
        name="list"
    )
    async def whitelist_list(
        self,
        ctx
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
                SELECT user_id
                FROM antinuke_whitelist
                WHERE guild_id = ?
            """, (
                ctx.guild.id,
            )) as cursor:

                data = await cursor.fetchall()

        if not data:

            return await ctx.send(
                embed=error_embed(
                    "No users are whitelisted."
                )
            )

        users = "\n".join(
            f"• <@{row[0]}>"
            for row in data
        )

        embed = base_embed(
            title="🛡️ Anti-Nuke Whitelist",
            description=users
        )

        await ctx.send(embed=embed)


# =========================
# LOAD
# =========================

async def setup(bot):

    await bot.add_cog(
        AntiNuke(bot)
    )
