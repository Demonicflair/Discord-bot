import discord

from discord.ext import commands

from utils.config import STAFF_ROLE_NAME


# =====================================
# OWNER
# =====================================

def is_owner():

    async def predicate(ctx):

        app = ctx.bot.application

        if not app:
            app = await ctx.bot.application_info()

        return ctx.author.id == app.owner.id

    return commands.check(predicate)


# =====================================
# ADMIN
# =====================================

def is_admin():

    async def predicate(ctx):

        return bool(

            ctx.guild and

            ctx.author.guild_permissions.administrator

        )

    return commands.check(predicate)


# =====================================
# OWNER OR ADMIN
# FIXED FOR ANTINUKE IMPORT
# =====================================

def is_owner_or_admin():

    async def predicate(ctx):

        app = ctx.bot.application

        if not app:
            app = await ctx.bot.application_info()

        if ctx.author.id == app.owner.id:
            return True

        return bool(

            ctx.guild and

            ctx.author.guild_permissions.administrator

        )

    return commands.check(predicate)


# =====================================
# STAFF
# =====================================

def is_staff():

    async def predicate(ctx):

        if not ctx.guild:
            return False

        if ctx.author.guild_permissions.administrator:
            return True

        role = discord.utils.get(
            ctx.guild.roles,
            name=STAFF_ROLE_NAME
        )

        return role in ctx.author.roles if role else False

    return commands.check(predicate)


# =====================================
# MODERATOR
# =====================================

def is_moderator():

    async def predicate(ctx):

        if not ctx.guild:
            return False

        perms = ctx.author.guild_permissions

        return any([

            perms.manage_messages,

            perms.kick_members,

            perms.ban_members,

            perms.moderate_members

        ])

    return commands.check(predicate)


def can_manage_guild():

    async def predicate(ctx):

        return bool(

            ctx.guild and

            ctx.author.guild_permissions.manage_guild

        )

    return commands.check(predicate)


def is_ticket_channel():

    async def predicate(ctx):

        return bool(

            ctx.guild and

            ctx.channel and

            ctx.channel.name.startswith("ticket-")

        )

    return commands.check(predicate)


def in_voice():

    async def predicate(ctx):

        return ctx.author.voice is not None

    return commands.check(predicate)


def bot_in_voice():

    async def predicate(ctx):

        return bool(

            ctx.guild and

            ctx.guild.voice_client

        )

    return commands.check(predicate)


def same_voice():

    async def predicate(ctx):

        if not ctx.guild:
            return False

        vc = ctx.guild.voice_client

        if not vc:
            return False

        if not ctx.author.voice:
            return False

        return ctx.author.voice.channel == vc.channel

    return commands.check(predicate)


def is_booster():

    async def predicate(ctx):

        return bool(

            ctx.guild and

            ctx.author.premium_since

        )

    return commands.check(predicate)


def guild_only():

    return commands.guild_only()


def dm_only():

    return commands.dm_only()
