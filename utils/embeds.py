import discord
from datetime import datetime

# =========================
# COLORS
# =========================

DEM_COLOR = 0x2B2D31

SUCCESS_COLOR = 0x57F287
ERROR_COLOR = 0xED4245
WARNING_COLOR = 0xFEE75C
INFO_COLOR = 0x5865F2

MOD_COLOR = 0x2B2D31
TICKET_COLOR = 0x2B2D31
LOG_COLOR = 0x313338

# =========================
# FOOTER
# =========================

DEFAULT_FOOTER = "Dem System"


# =========================
# BASE EMBED
# =========================

def base_embed(
    title: str = None,
    description: str = None,
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


# =========================
# SUCCESS EMBED
# =========================

def success_embed(
    description: str,
    title: str = "✅ Success"
):

    embed = base_embed(
        title=title,
        description=description,
        color=SUCCESS_COLOR
    )

    return embed


# =========================
# ERROR EMBED
# =========================

def error_embed(
    description: str,
    title: str = "❌ Error"
):

    embed = base_embed(
        title=title,
        description=description,
        color=ERROR_COLOR
    )

    return embed


# =========================
# WARNING EMBED
# =========================

def warning_embed(
    description: str,
    title: str = "⚠️ Warning"
):

    embed = base_embed(
        title=title,
        description=description,
        color=WARNING_COLOR
    )

    return embed


# =========================
# INFO EMBED
# =========================

def info_embed(
    description: str,
    title: str = "ℹ️ Information"
):

    embed = base_embed(
        title=title,
        description=description,
        color=INFO_COLOR
    )

    return embed


# =========================
# MODERATION EMBED
# =========================

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
        value=reason,
        inline=False
    )

    if hasattr(target, "display_avatar"):

        embed.set_thumbnail(
            url=target.display_avatar.url
        )

    return embed


# =========================
# TICKET EMBED
# =========================

def ticket_embed(
    user,
    description: str = None
):

    embed = base_embed(
        title="🎫 Support Ticket",
        description=(
            description
            or
            (
                f"Welcome {user.mention}\n\n"
                "Please explain your issue.\n"
                "A staff member will assist you shortly."
            )
        ),
        color=TICKET_COLOR
    )

    embed.add_field(
        name="Ticket Owner",
        value=f"{user.mention}",
        inline=False
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    return embed


# =========================
# LOG EMBED
# =========================

def log_embed(
    title: str,
    description: str,
    color: int = LOG_COLOR
):

    embed = base_embed(
        title=title,
        description=description,
        color=color
    )

    return embed


# =========================
# USER INFO EMBED
# =========================

def user_info_embed(member: discord.Member):

    embed = base_embed(
        color=member.color
    )

    embed.set_author(
        name=f"{member}",
        icon_url=member.display_avatar.url
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="🆔 User ID",
        value=f"`{member.id}`",
        inline=True
    )

    embed.add_field(
        name="📅 Created",
        value=f"<t:{int(member.created_at.timestamp())}:R>",
        inline=True
    )

    embed.add_field(
        name="📥 Joined",
        value=f"<t:{int(member.joined_at.timestamp())}:R>",
        inline=True
    )

    embed.add_field(
        name="🛡️ Top Role",
        value=member.top_role.mention,
        inline=True
    )

    embed.add_field(
        name="🤖 Bot",
        value="Yes" if member.bot else "No",
        inline=True
    )

    roles = [r.mention for r in member.roles[1:]]

    embed.add_field(
        name=f"🎭 Roles [{len(roles)}]",
        value=" ".join(roles[:10]) if roles else "None",
        inline=False
    )

    return embed


# =========================
# SERVER INFO EMBED
# =========================

def server_info_embed(guild: discord.Guild):

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
        value=f"{guild.owner}",
        inline=True
    )

    embed.add_field(
        name="👥 Members",
        value=f"`{guild.member_count}`",
        inline=True
    )

    embed.add_field(
        name="📅 Created",
        value=f"<t:{int(guild.created_at.timestamp())}:D>",
        inline=True
    )

    embed.add_field(
        name="💬 Channels",
        value=(
            f"Text: `{len(guild.text_channels)}`\n"
            f"Voice: `{len(guild.voice_channels)}`"
        ),
        inline=True
    )

    embed.add_field(
        name="🎭 Roles",
        value=f"`{len(guild.roles)}`",
        inline=True
    )

    embed.add_field(
        name="😀 Emojis",
        value=f"`{len(guild.emojis)}`",
        inline=True
    )

    return embed


# =========================
# PING EMBED
# =========================

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
        f"**Gateway:** `{gateway}ms`\n"
        f"**Rest API:** `{rest}ms`\n"
        f"**Status:** {status}"
    )

    return embed


# =========================
# ECONOMY EMBED
# =========================

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
        value=f"💵 `{balance:,}`",
        inline=True
    )

    embed.add_field(
        name="Bank",
        value=f"🏦 `{bank:,}`",
        inline=True
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    return embed


# =========================
# LEVEL EMBED
# =========================

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
        value=f"`{xp}/{required}`",
        inline=True
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    return embed
