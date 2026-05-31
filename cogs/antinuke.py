import asyncio
import time
import aiosqlite
import discord

from collections import defaultdict
from discord.ext import commands, tasks

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
    ANTI_NUKE_LIMIT,
    WHITELIST
)


class AntiNuke(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.cooldowns = defaultdict(list)

        self.cleanup.start()

    def cog_unload(self):

        self.cleanup.cancel()

    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            CREATE TABLE IF NOT EXISTS antinuke_whitelist(

                guild_id INTEGER,

                user_id INTEGER,

                PRIMARY KEY(guild_id,user_id)

            )

            """)

            await db.commit()

    @tasks.loop(minutes=30)
    async def cleanup(self):

        now = time.time()

        remove = []

        for key, timestamps in self.cooldowns.items():

            filtered = [

                t for t in timestamps

                if now - t <= 20

            ]

            if filtered:

                self.cooldowns[key] = filtered

            else:

                remove.append(key)

        for key in remove:

            self.cooldowns.pop(
                key,
                None
            )

    async def is_whitelisted(

        self,

        guild_id,

        user_id

    ):

        if user_id in WHITELIST:

            return True

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""

            SELECT 1

            FROM antinuke_whitelist

            WHERE guild_id=?

            AND user_id=?

            """,(guild_id,user_id)) as cursor:

                return await cursor.fetchone() is not None

    async def check_threshold(

        self,

        guild_id,

        user_id,

        action

    ):

        key=(guild_id,user_id,action)

        now=time.time()

        self.cooldowns[key].append(now)

        self.cooldowns[key]=[

            t for t in self.cooldowns[key]

            if now-t <=10

        ]

        return len(self.cooldowns[key]) >= ANTI_NUKE_LIMIT

    async def punish(

        self,

        guild,

        member,

        reason

    ):

        if not member:

            return

        bot_member = guild.me or guild.get_member(
            self.bot.user.id
        )

        if not bot_member:

            return

        if member.id == guild.owner_id:

            return

        if member.top_role >= bot_member.top_role:

            return

        try:

            await member.ban(

                reason=f"Dem AntiNuke | {reason}",

                delete_message_seconds=86400

            )

            await dispatch_log(

                guild=guild,

                log_type="antinuke",

                content=(

                    f"User: {member}\n"

                    f"Reason: {reason}\n"

                    f"Action: Ban"

                ),

                user_id=member.id

            )

        except discord.Forbidden:

            try:

                await member.edit(

                    roles=[],

                    reason="Emergency Lockdown"

                )

            except:

                pass

    async def fetch_entry(

        self,

        guild,

        action

    ):

        await asyncio.sleep(1)

        try:

            async for entry in guild.audit_logs(

                limit=1,

                action=action

            ):

                return entry

        except:

            return None

    async def process_event(

        self,

        guild,

        action,

        action_name,

        reason,

        cleanup=None

    ):

        entry = await self.fetch_entry(
            guild,
            action
        )

        if not entry:

            return

        user = entry.user

        if not user:

            return

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

            action_name

        )

        if not triggered:

            return

        if cleanup:

            try:

                await cleanup()

            except:

                pass

        member = guild.get_member(
            user.id
        )

        await self.punish(

            guild,

            member,

            reason

        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(
        self,
        channel
    ):

        async def restore():

            cloned = await channel.clone(
                reason="AntiNuke Restore"
            )

            await cloned.edit(
                position=channel.position
            )

        await self.process_event(

            channel.guild,

            discord.AuditLogAction.channel_delete,

            "channel_delete",

            "Mass Channel Delete",

            restore

        )

    @commands.Cog.listener()
    async def on_guild_channel_create(
        self,
        channel
    ):

        await self.process_event(

            channel.guild,

            discord.AuditLogAction.channel_create,

            "channel_create",

            "Mass Channel Create",

            lambda: channel.delete()

        )

    @commands.Cog.listener()
    async def on_guild_role_delete(
        self,
        role
    ):

        await self.process_event(

            role.guild,

            discord.AuditLogAction.role_delete,

            "role_delete",

            "Mass Role Delete"

        )

    @commands.Cog.listener()
    async def on_guild_role_create(
        self,
        role
    ):

        await self.process_event(

            role.guild,

            discord.AuditLogAction.role_create,

            "role_create",

            "Mass Role Create",

            lambda: role.delete()

        )

    @commands.Cog.listener()
    async def on_webhooks_update(
        self,
        channel
    ):

        async def cleanup():

            webhooks = await channel.webhooks()

            for webhook in webhooks:

                try:

                    await webhook.delete()

                except:

                    pass

        await self.process_event(

            channel.guild,

            discord.AuditLogAction.webhook_create,

            "webhook_create",

            "Mass Webhook Create",

            cleanup

        )

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member
    ):

        if not member.bot:

            return

        guild = member.guild

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

                reason="Unauthorized Bot"

            )

        except:

            pass

        await self.punish(

            guild,

            guild.get_member(user.id),

            "Unauthorized Bot Add"

        )

    @commands.hybrid_group(

        name="antinuke",

        description="Manage AntiNuke"

    )

    @is_owner_or_admin()

    async def antinuke(

        self,

        ctx

    ):

        if ctx.invoked_subcommand is None:

            await ctx.send(

                embed=base_embed(

                    title="AntiNuke",

                    description=(

                        "`/antinuke whitelist`\n"

                        "`/antinuke unwhitelist`\n"

                        "`/antinuke list`"

                    )

                )

            )

    @antinuke.command()
    async def whitelist(

        self,

        ctx,

        user: discord.Member

    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            INSERT OR REPLACE INTO antinuke_whitelist

            VALUES (?,?)

            """,(ctx.guild.id,user.id))

            await db.commit()

        await ctx.send(

            embed=success_embed(

                f"{user.mention} added."

            )

        )

    @antinuke.command()
    async def unwhitelist(

        self,

        ctx,

        user: discord.Member

    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""

            DELETE FROM antinuke_whitelist

            WHERE guild_id=?

            AND user_id=?

            """,(ctx.guild.id,user.id))

            await db.commit()

        await ctx.send(

            embed=success_embed(

                f"{user.mention} removed."

            )

        )

    @antinuke.command(name="list")
    async def whitelist_list(
        self,
        ctx
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""

            SELECT user_id

            FROM antinuke_whitelist

            WHERE guild_id=?

            """,(ctx.guild.id,)) as cursor:

                data=await cursor.fetchall()

        if not data:

            return await ctx.send(

                embed=error_embed(

                    "Whitelist empty."

                )

            )

        users="\n".join(

            f"• <@{x[0]}>"

            for x in data

        )

        await ctx.send(

            embed=base_embed(

                title="Whitelist",

                description=users

            )

        )


async def setup(bot):

    await bot.add_cog(
        AntiNuke(bot)
    )
