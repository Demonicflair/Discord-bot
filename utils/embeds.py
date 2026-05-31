import discord

from datetime import datetime
from typing import Optional


# ==================================================
# COLORS
# ==================================================

DEM_COLOR = 0x2B2D31

SUCCESS_COLOR = 0x57F287
ERROR_COLOR = 0xED4245
WARNING_COLOR = 0xFEE75C
INFO_COLOR = 0x5865F2

MOD_COLOR = DEM_COLOR
TICKET_COLOR = DEM_COLOR
LOG_COLOR = 0x313338

DEFAULT_FOOTER = "Dem System"


# ==================================================
# BASE EMBED
# ==================================================

def base_embed(
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: int = DEM_COLOR
):

    embed = discord.Embed(

        title=title,

        description=description,

        color=color,

        timestamp=datetime.utcnow()

    )

    embed.set_footer(
        text=DEFAULT_FOOTER
    )

    return embed


# ==================================================
# SIMPLE EMBEDS
# ==================================================

def success_embed(
    description: str,
    title: str = "✅ Success"
):

    return base_embed(
        title=title,
        description=description,
        color=SUCCESS_COLOR
    )


def error_embed(
    description: str,
    title: str = "❌ Error"
):

    return base_embed(
        title=title,
        description=description,
        color=ERROR_COLOR
    )


def warning_embed(
    description: str,
    title: str = "⚠️ Warning"
):

    return base_embed(
        title=title,
        description=description,
        color=WARNING_COLOR
    )


def info_embed(
    description: str,
    title: str = "ℹ️ Information"
):

    return base_embed(
        title=title,
        description=description,
        color=INFO_COLOR
    )


# ==================================================
# MODERATION
# ==================================================

def moderation_embed(
    action: str,
    moderator,
    target,
    reason: str = "No reason provided",
    color: int = MOD_COLOR
):

    embed = base_embed(

        title=f"🛡️ Moderation • {action}",

        color=color

    )

    embed.add_field(

        name="Moderator",

        value=f"{moderator.mention}\n`{moderator.id}`",

        inline=True

    )

    embed.add_field(

        name="Target",

        value=f"{target.mention}\n`{target.id}`",

        inline=True

    )

    embed.add_field(

        name="Reason",

        value=reason[:1024],

        inline=False

    )

    if getattr(
        target,
        "display_avatar",
        None
    ):

        embed.set_thumbnail(

            url=target.display_avatar.url

        )

    return embed


# ==================================================
# TICKETS
# ==================================================

def ticket_embed(
    user,
    description: str = None
):

    embed = base_embed(

        title="🎫 Support Ticket",

        description=description or (

            f"Welcome {user.mention}\n\n"

            "Please explain your issue.\n"

            "A staff member will assist shortly."

        ),

        color=TICKET_COLOR

    )

    embed.add_field(

        name="Ticket Owner",

        value=user.mention,

        inline=False

    )

    embed.set_thumbnail(

        url=user.display_avatar.url

    )

    return embed


# ==================================================
# LOGS
# ==================================================

def log_embed(
    title: str,
    description: str,
    color: int = LOG_COLOR
):

    return base_embed(

        title=title,

        description=description,

        color=color

    )


# ==================================================
# USER INFO
# ==================================================

def user_info_embed(
    member: discord.Member
):

    embed = base_embed(
        color=member.color
    )

    embed.set_author(

        name=str(member),

        icon_url=member.display_avatar.url

    )

    embed.set_thumbnail(

        url=member.display_avatar.url

    )

    embed.add_field(

        name="🆔 User ID",

        value=f"`{member.id}`"

    )

    embed.add_field(

        name="📅 Created",

        value=f"<t:{int(member.created_at.timestamp())}:R>"

    )

    joined = (

        f"<t:{int(member.joined_at.timestamp())}:R>"

        if member.joined_at

        else "Unknown"

    )

    embed.add_field(

        name="📥 Joined",

        value=joined

    )

    embed.add_field(

        name="🛡️ Top Role",

        value=member.top_role.mention

    )

    embed.add_field(

        name="🤖 Bot",

        value="Yes" if member.bot else "No"

    )

    roles = [

        r.mention

        for r in member.roles[1:]

    ]

    embed.add_field(

        name=f"🎭 Roles [{len(roles)}]",

        value=(

            " ".join(

                roles[:15]

            )

            if roles

            else "None"

        ),

        inline=False

    )

    return embed


# ==================================================
# SERVER INFO
# ==================================================

def server_info_embed(
    guild: discord.Guild
):

    embed = base_embed(

        title=f"🌍 {guild.name}",

        color=DEM_COLOR

    )

    if guild.icon:

        embed.set_thumbnail(

            url=guild.icon.url

        )

    embed.add_field(

        name="👑 Owner",

        value=str(guild.owner)

    )

    embed.add_field(

        name="👥 Members",

        value=str(guild.member_count)

    )

    embed.add_field(

        name="📅 Created",

        value=f"<t:{int(guild.created_at.timestamp())}:D>"

    )

    embed.add_field(

        name="💬 Channels",

        value=(

            f"Text: {len(guild.text_channels)}\n"

            f"Voice: {len(guild.voice_channels)}"

        )

    )

    embed.add_field(

        name="🎭 Roles",

        value=str(

            len(guild.roles)

        )

    )

    embed.add_field(

        name="😀 Emojis",

        value=str(

            len(guild.emojis)

        )

    )

    return embed


# ==================================================
# PING
# ==================================================

def ping_embed(
    gateway: int,
    rest: int
):

    if gateway < 100:

        status = "🟢 Excellent"

    elif gateway < 250:

        status = "🟡 Stable"

    else:

        status = "🔴 High Latency"

    embed = base_embed(

        title="🏓 Pong",

        color=INFO_COLOR

    )

    embed.description = (

        f"Gateway: `{gateway}ms`\n"

        f"REST: `{rest}ms`\n"

        f"Status: {status}"

    )

    return embed


# ==================================================
# ECONOMY
# ==================================================

def economy_embed(
    user,
    balance: int,
    bank: int = 0
):

    embed = base_embed(

        title=f"💰 {user.name}'s Balance",

        color=SUCCESS_COLOR

    )

    embed.add_field(

        name="Wallet",

        value=f"`{balance:,}`"

    )

    embed.add_field(

        name="Bank",

        value=f"`{bank:,}`"

    )

    embed.set_thumbnail(

        url=user.display_avatar.url

    )

    return embed


# ==================================================
# LEVEL
# ==================================================

def level_embed(
    user,
    level: int,
    xp: int,
    required: int
):

    embed = base_embed(

        title="⭐ Level Up",

        description=(

            f"{user.mention} reached "

            f"Level **{level}**"

        ),

        color=INFO_COLOR

    )

    embed.add_field(

        name="XP",

        value=f"`{xp}/{required}`"

    )

    embed.set_thumbnail(

        url=user.display_avatar.url

    )

    return embed
