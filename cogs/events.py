import discord

from discord.ext import commands

from utils.dispatch import dispatch_log


MAX_LOG_LENGTH = 1500


class Events(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # ==================================
    # SAFE CONTENT
    # ==================================

    def truncate(

        self,

        text: str | None

    ):

        if not text:

            return "*No text content*"

        if len(text) > MAX_LOG_LENGTH:

            return text[:MAX_LOG_LENGTH] + "..."

        return text

    # ==================================
    # MESSAGE DELETE
    # ==================================

    @commands.Cog.listener()
    async def on_message_delete(

        self,

        message: discord.Message

    ):

        if not message.guild:

            return

        if message.author.bot:

            return

        try:

            content = self.truncate(

                message.content

            )

            await dispatch_log(

                message.guild,

                "message_delete",

                (
                    f"🗑️ Message Deleted\n\n"

                    f"Channel: {message.channel.mention}\n"

                    f"Author: {message.author}"

                    f" ({message.author.id})\n\n"

                    f"Content:\n"

                    f"{content}"

                ),

                user_id=message.author.id

            )

        except Exception:

            pass

    # ==================================
    # MESSAGE EDIT
    # ==================================

    @commands.Cog.listener()
    async def on_message_edit(

        self,

        before: discord.Message,

        after: discord.Message

    ):

        if not before.guild:

            return

        if before.author.bot:

            return

        if before.content == after.content:

            return

        try:

            old = self.truncate(

                before.content

            )

            new = self.truncate(

                after.content

            )

            await dispatch_log(

                before.guild,

                "message_edit",

                (

                    f"📝 Message Edited\n\n"

                    f"Channel: {before.channel.mention}\n"

                    f"Author: {before.author}"

                    f" ({before.author.id})\n\n"

                    f"Before:\n"

                    f"{old}\n\n"

                    f"After:\n"

                    f"{new}"

                ),

                user_id=before.author.id

            )

        except Exception:

            pass

    # ==================================
    # MEMBER UPDATE
    # ==================================

    @commands.Cog.listener()
    async def on_member_update(

        self,

        before: discord.Member,

        after: discord.Member

    ):

        try:

            # Nicknames

            if before.nick != after.nick:

                await dispatch_log(

                    after.guild,

                    "member_update",

                    (

                        f"🎨 Nickname Changed\n\n"

                        f"User: {after.mention}\n"

                        f"Old: `{before.nick or 'None'}`\n"

                        f"New: `{after.nick or 'None'}`"

                    ),

                    user_id=after.id

                )

            # Roles

            before_roles = set(before.roles)

            after_roles = set(after.roles)

            added = after_roles - before_roles
            removed = before_roles - after_roles

            if added or removed:

                text = []

                if added:

                    text.append(

                        "Added:\n"

                        +

                        "\n".join(

                            r.mention

                            for r in added

                            if not r.is_default()

                        )

                    )

                if removed:

                    text.append(

                        "Removed:\n"

                        +

                        "\n".join(

                            r.mention

                            for r in removed

                            if not r.is_default()

                        )

                    )

                await dispatch_log(

                    after.guild,

                    "role_update",

                    (

                        f"🎭 Roles Updated\n\n"

                        f"User: {after.mention}\n\n"

                        +

                        "\n\n".join(text)

                    ),

                    user_id=after.id

                )

        except Exception:

            pass

    # ==================================
    # VOICE LOGS
    # ==================================

    @commands.Cog.listener()
    async def on_voice_state_update(

        self,

        member,

        before,

        after

    ):

        # Ignore mute/deafen changes

        if before.channel == after.channel:

            return

        try:

            if before.channel is None:

                msg = (

                    f"📥 {member.mention} joined "

                    f"`{after.channel.name}`"

                )

            elif after.channel is None:

                msg = (

                    f"📤 {member.mention} left "

                    f"`{before.channel.name}`"

                )

            else:

                msg = (

                    f"🔄 {member.mention} moved\n"

                    f"`{before.channel.name}` "

                    f"→ "

                    f"`{after.channel.name}`"

                )

            await dispatch_log(

                member.guild,

                "voice",

                msg,

                user_id=member.id

            )

        except Exception:

            pass


async def setup(bot):

    await bot.add_cog(

        Events(bot)

    )
