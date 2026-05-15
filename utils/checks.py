# utils/checks.py

import discord

from discord.ext import commands

from utils.config import OWNER_IDS
from utils.config import STAFF_ROLE_NAME


# =========================
# OWNER CHECK
# =========================

def is_owner():

    async def predicate(ctx):

        return ctx.author.id in OWNER_IDS

    return commands.check(predicate)


# =========================
# ADMIN CHECK
# =========================

def is_admin():

    async def predicate(ctx):

        return ctx.author.guild_permissions.administrator

    return commands.check(predicate)


# =========================
# STAFF ROLE CHECK
# =========================

def is_staff():

    async def predicate(ctx):

        if ctx.author.guild_permissions.administrator:
            return True

        role = discord.utils.get(
            ctx.guild.roles,
            name=STAFF_ROLE_NAME
        )

        if not role:
            return False

        return role in ctx.author.roles

    return commands.check(predicate)


# =========================
# MODERATOR CHECK
# =========================

def is_moderator():

    async def predicate(ctx):

        perms = ctx.author.guild_permissions

        return (
            perms.manage_messages
            or perms.kick_members
            or perms.ban_members
        )

    return commands.check(predicate)


# =========================
# MANAGE GUILD CHECK
# =========================

def can_manage_guild():

    async def predicate(ctx):

        return ctx.author.guild_permissions.manage_guild

    return commands.check(predicate)


# =========================
# TICKET CHANNEL CHECK
# =========================

def is_ticket_channel():

    async def predicate(ctx):

        return (
            ctx.channel.name.startswith("ticket-")
        )

    return commands.check(predicate)


# =========================
# VOICE CHANNEL CHECK
# =========================

def in_voice():

    async def predicate(ctx):

        return (
            ctx.author.voice is not None
        )

    return commands.check(predicate)


# =========================
# BOT VOICE CHECK
# =========================

def bot_in_voice():

    async def predicate(ctx):

        return (
            ctx.guild.voice_client is not None
        )

    return commands.check(predicate)


# =========================
# SAME VC CHECK
# =========================

def same_voice():

    async def predicate(ctx):

        if not ctx.author.voice:
            return False

        if not ctx.guild.voice_client:
            return False

        return (
            ctx.author.voice.channel
            ==
            ctx.guild.voice_client.channel
        )

    return commands.check(predicate)


# =========================
# BOOSTER CHECK
# =========================

def is_booster():

    async def predicate(ctx):

        return ctx.author.premium_since is not None

    return commands.check(predicate)


# =========================
# NSFW CHECK
# =========================

def is_nsfw():

    async def predicate(ctx):

        return ctx.channel.is_nsfw()

    return commands.check(predicate)


# =========================
# PREMIUM GUILD CHECK
# =========================

def premium_guild():

    async def predicate(ctx):

        return (
            ctx.guild.premium_tier >= 2
        )

    return commands.check(predicate)


# =========================
# WHITELIST ROLE CHECK
# =========================

def has_role(role_name: str):

    async def predicate(ctx):

        role = discord.utils.get(
            ctx.guild.roles,
            name=role_name
        )

        if not role:
            return False

        return role in ctx.author.roles

    return commands.check(predicate)


# =========================
# BOT PERMISSION CHECK
# =========================

def bot_has_permissions(**perms):

    async def predicate(ctx):

        permissions = ctx.channel.permissions_for(
            ctx.guild.me
        )

        missing = []

        for perm, value in perms.items():

            if getattr(permissions, perm) != value:

                missing.append(perm)

        if missing:

            raise commands.BotMissingPermissions(
                missing
            )

        return True

    return commands.check(predicate)


# =========================
# USER PERMISSION CHECK
# =========================

def user_has_permissions(**perms):

    async def predicate(ctx):

        permissions = ctx.channel.permissions_for(
            ctx.author
        )

        missing = []

        for perm, value in perms.items():

            if getattr(permissions, perm) != value:

                missing.append(perm)

        if missing:

            raise commands.MissingPermissions(
                missing
            )

        return True

    return commands.check(predicate)


# =========================
# BLACKLIST CHECK
# =========================

def not_blacklisted(blacklist: list):

    async def predicate(ctx):

        return ctx.author.id not in blacklist

    return commands.check(predicate)


# =========================
# COOLDOWN WRAPPER
# =========================

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


# =========================
# GUILD ONLY CHECK
# =========================

def guild_only():

    async def predicate(ctx):

        return ctx.guild is not None

    return commands.check(predicate)


# =========================
# DM ONLY CHECK
# =========================

def dm_only():

    async def predicate(ctx):

        return ctx.guild is None

    return commands.check(predicate)
