import discord

from discord.ext import commands

from utils.config import STAFF_ROLE_NAME


# ==================================================
# OWNER CHECK
# ==================================================

def is_owner():

    async def predicate(ctx):

        app = ctx.bot.application

        if not app:

            app = await ctx.bot.application_info()

        return ctx.author.id == app.owner.id

    return commands.check(
        predicate
    )


# ==================================================
# ADMIN CHECK
# ==================================================

def is_admin():

    async def predicate(ctx):

        return (

            ctx.guild

            and

            ctx.author.guild_permissions.administrator

        )

    return commands.check(
        predicate
    )


# ==================================================
# STAFF CHECK
# ==================================================

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

        if not role:

            return False

        return role in ctx.author.roles

    return commands.check(
        predicate
    )


# ==================================================
# MODERATOR CHECK
# ==================================================

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

    return commands.check(
        predicate
    )


# ==================================================
# MANAGE GUILD
# ==================================================

def can_manage_guild():

    async def predicate(ctx):

        return (

            ctx.guild

            and

            ctx.author.guild_permissions.manage_guild

        )

    return commands.check(
        predicate
    )


# ==================================================
# TICKET CHANNEL
# ==================================================

def is_ticket_channel():

    async def predicate(ctx):

        return (

            ctx.guild

            and

            ctx.channel

            and

            ctx.channel.name.startswith(

                "ticket-"

            )

        )

    return commands.check(
        predicate
    )


# ==================================================
# VOICE CHECKS
# ==================================================

def in_voice():

    async def predicate(ctx):

        return (

            ctx.author.voice

            is not None

        )

    return commands.check(
        predicate
    )


def bot_in_voice():

    async def predicate(ctx):

        return (

            ctx.guild

            and

            ctx.guild.voice_client

            is not None

        )

    return commands.check(
        predicate
    )


def same_voice():

    async def predicate(ctx):

        if not ctx.guild:

            return False

        if not ctx.author.voice:

            return False

        vc = ctx.guild.voice_client

        if not vc:

            return False

        return (

            ctx.author.voice.channel

            ==

            vc.channel

        )

    return commands.check(
        predicate
    )


# ==================================================
# BOOSTER
# ==================================================

def is_booster():

    async def predicate(ctx):

        return (

            ctx.guild

            and

            ctx.author.premium_since

            is not None

        )

    return commands.check(
        predicate
    )


# ==================================================
# NSFW
# ==================================================

def is_nsfw():

    async def predicate(ctx):

        return (

            hasattr(

                ctx.channel,

                "is_nsfw"

            )

            and

            ctx.channel.is_nsfw()

        )

    return commands.check(
        predicate
    )


# ==================================================
# PREMIUM GUILD
# ==================================================

def premium_guild():

    async def predicate(ctx):

        return (

            ctx.guild

            and

            ctx.guild.premium_tier >= 2

        )

    return commands.check(
        predicate
    )


# ==================================================
# ROLE CHECK
# ==================================================

def has_role(

    role_name: str

):

    async def predicate(ctx):

        if not ctx.guild:

            return False

        role = discord.utils.get(

            ctx.guild.roles,

            name=role_name

        )

        return (

            role

            and

            role in ctx.author.roles

        )

    return commands.check(
        predicate
    )


# ==================================================
# BOT PERMISSIONS
# ==================================================

def bot_has_permissions(

    **perms

):

    async def predicate(ctx):

        me = ctx.guild.me

        permissions = (

            ctx.channel.permissions_for(

                me

            )

        )

        missing = [

            perm

            for perm,

            value

            in perms.items()

            if getattr(

                permissions,

                perm,

                None

            ) != value

        ]

        if missing:

            raise commands.BotMissingPermissions(

                missing

            )

        return True

    return commands.check(
        predicate
    )


# ==================================================
# USER PERMISSIONS
# ==================================================

def user_has_permissions(

    **perms

):

    async def predicate(ctx):

        permissions = (

            ctx.channel.permissions_for(

                ctx.author

            )

        )

        missing = [

            perm

            for perm,

            value

            in perms.items()

            if getattr(

                permissions,

                perm,

                None

            ) != value

        ]

        if missing:

            raise commands.MissingPermissions(

                missing

            )

        return True

    return commands.check(
        predicate
    )


# ==================================================
# BLACKLIST
# ==================================================

def not_blacklisted(

    blacklist: list

):

    async def predicate(ctx):

        return (

            ctx.author.id

            not in blacklist

        )

    return commands.check(
        predicate
    )


# ==================================================
# COOLDOWN
# ==================================================

def cooldown(

    rate: int,

    per: int,

    bucket=commands.BucketType.user

):

    return commands.cooldown(

        rate,

        per,

        bucket

    )


# ==================================================
# GUILD ONLY
# ==================================================

def guild_only():

    return commands.guild_only()


# ==================================================
# DM ONLY
# ==================================================

def dm_only():

    return commands.dm_only()
