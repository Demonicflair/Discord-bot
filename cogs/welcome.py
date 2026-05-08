# welcome.py

import discord
from discord.ext import commands
import sqlite3

from utils.logger import get_logs, save_log, is_log_enabled

# =========================
# DATABASE
# =========================
db = sqlite3.connect("welcome.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS welcome_settings(
    guild_id INTEGER PRIMARY KEY,
    welcome_channel INTEGER,
    leave_channel INTEGER,
    welcome_message TEXT,
    leave_message TEXT,
    autorole INTEGER
)
""")

db.commit()

# =========================
# EMBED
# =========================
def build_embed(title, desc, color):

    embed = discord.Embed(
        title=title,
        description=desc,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    return embed


# =========================
# COG
# =========================
class Welcome(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # FETCH SETTINGS
    # =========================
    def get_data(self, guild_id):

        cursor.execute(
            "SELECT * FROM welcome_settings WHERE guild_id=?",
            (guild_id,)
        )

        return cursor.fetchone()

    # =========================
    # MEMBER JOIN
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):

        data = self.get_data(member.guild.id)

        if not data:
            return

        channel_id = data[1]
        message = data[3]
        autorole = data[5]

        channel = member.guild.get_channel(channel_id)

        if autorole:

            role = member.guild.get_role(autorole)

            if role:

                try:
                    await member.add_roles(role)

                except:
                    pass

        if channel:

            text = (
                message
                .replace("{user}", member.mention)
                .replace("{server}", member.guild.name)
                .replace("{members}", str(member.guild.member_count))
            )

            embed = build_embed(
                "👋 Welcome",
                text,
                discord.Color.green()
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            await channel.send(embed=embed)

        logs = get_logs(member.guild.id)

        if logs and is_log_enabled(member.guild.id, "welcome"):

            log_channel = member.guild.get_channel(logs[1])

            if log_channel:

                await log_channel.send(
                    embed=build_embed(
                        "📥 Member Joined",
                        f"{member.mention} joined the server.",
                        discord.Color.green()
                    )
                )

        save_log(
            member.guild.id,
            member.id,
            "welcome",
            f"{member} joined"
        )

    # =========================
    # MEMBER LEAVE
    # =========================
    @commands.Cog.listener()
    async def on_member_remove(self, member):

        data = self.get_data(member.guild.id)

        if not data:
            return

        channel_id = data[2]
        message = data[4]

        channel = member.guild.get_channel(channel_id)

        if channel:

            text = (
                message
                .replace("{user}", str(member))
                .replace("{server}", member.guild.name)
                .replace("{members}", str(member.guild.member_count))
            )

            embed = build_embed(
                "💔 Member Left",
                text,
                discord.Color.red()
            )

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

            await channel.send(embed=embed)

        logs = get_logs(member.guild.id)

        if logs and is_log_enabled(member.guild.id, "welcome"):

            log_channel = member.guild.get_channel(logs[1])

            if log_channel:

                await log_channel.send(
                    embed=build_embed(
                        "📤 Member Left",
                        f"{member} left the server.",
                        discord.Color.red()
                    )
                )

        save_log(
            member.guild.id,
            member.id,
            "welcome",
            f"{member} left"
        )

    # =========================
    # SET WELCOME CHANNEL
    # =========================
    @commands.hybrid_command(
        name="setwelcomechannel",
        help="Set welcome channel.",
        extras={
            "example": "!setwelcomechannel #welcome",
            "tips": "Members will be welcomed there."
        }
    )
    @commands.has_permissions(administrator=True)
    async def setwelcomechannel(
        self,
        ctx,
        channel: discord.TextChannel = None
    ):
        """Set welcome channel."""

        if not channel:

            return await ctx.send(
                "❌ Usage: !setwelcomechannel #channel"
            )

        cursor.execute(
            "INSERT OR REPLACE INTO welcome_settings(guild_id, welcome_channel) VALUES (?, ?)",
            (ctx.guild.id, channel.id)
        )

        db.commit()

        await ctx.send(
            embed=build_embed(
                "✅ Welcome Channel Set",
                f"{channel.mention}",
                discord.Color.green()
            )
        )

    # =========================
    # SET LEAVE CHANNEL
    # =========================
    @commands.hybrid_command(
        name="setleavechannel",
        help="Set leave channel.",
        extras={
            "example": "!setleavechannel #goodbye",
            "tips": "Leave logs go there."
        }
    )
    @commands.has_permissions(administrator=True)
    async def setleavechannel(
        self,
        ctx,
        channel: discord.TextChannel = None
    ):
        """Set leave channel."""

        if not channel:

            return await ctx.send(
                "❌ Usage: !setleavechannel #channel"
            )

        cursor.execute(
            """
            INSERT OR REPLACE INTO
            welcome_settings(guild_id, leave_channel)
            VALUES (?, ?)
            """,
            (ctx.guild.id, channel.id)
        )

        db.commit()

        await ctx.send(
            embed=build_embed(
                "✅ Leave Channel Set",
                f"{channel.mention}",
                discord.Color.green()
            )
        )

    # =========================
    # SET WELCOME MESSAGE
    # =========================
    @commands.hybrid_command(
        name="setwelcome",
        help="Set welcome message.",
        extras={
            "example": "!setwelcome Welcome {user}",
            "tips": "Use {user}, {server}, {members}"
        }
    )
    @commands.has_permissions(administrator=True)
    async def setwelcome(
        self,
        ctx,
        *,
        message=None
    ):
        """Set welcome message."""

        if not message:

            return await ctx.send(
                "❌ Usage: !setwelcome <message>"
            )

        cursor.execute(
            """
            UPDATE welcome_settings
            SET welcome_message=?
            WHERE guild_id=?
            """,
            (message, ctx.guild.id)
        )

        db.commit()

        await ctx.send("✅ Welcome message updated.")

    # =========================
    # SET LEAVE MESSAGE
    # =========================
    @commands.hybrid_command(
        name="setleave",
        help="Set leave message.",
        extras={
            "example": "!setleave Goodbye {user}",
            "tips": "Use variables."
        }
    )
    @commands.has_permissions(administrator=True)
    async def setleave(
        self,
        ctx,
        *,
        message=None
    ):
        """Set leave message."""

        if not message:

            return await ctx.send(
                "❌ Usage: !setleave <message>"
            )

        cursor.execute(
            """
            UPDATE welcome_settings
            SET leave_message=?
            WHERE guild_id=?
            """,
            (message, ctx.guild.id)
        )

        db.commit()

        await ctx.send("✅ Leave message updated.")

    # =========================
    # AUTOROLE
    # =========================
    @commands.hybrid_command(
        name="setautorole",
        help="Set auto role.",
        extras={
            "example": "!setautorole @Member",
            "tips": "New users get this role."
        }
    )
    @commands.has_permissions(manage_roles=True)
    async def setautorole(
        self,
        ctx,
        role: discord.Role = None
    ):
        """Set autorole."""

        if not role:

            return await ctx.send(
                "❌ Usage: !setautorole @role"
            )

        cursor.execute(
            """
            UPDATE welcome_settings
            SET autorole=?
            WHERE guild_id=?
            """,
            (role.id, ctx.guild.id)
        )

        db.commit()

        await ctx.send(
            f"✅ Autorole set to {role.mention}"
        )

    # =========================
    # TEST WELCOME
    # =========================
    @commands.hybrid_command(
        name="testwelcome",
        help="Test welcome message.",
        extras={
            "example": "!testwelcome",
            "tips": "Preview the welcome."
        }
    )
    async def testwelcome(self, ctx):
        """Test welcome."""

        member = ctx.author

        embed = build_embed(
            "👋 Welcome",
            (
                f"Welcome {member.mention}\n"
                f"You are member #{ctx.guild.member_count}"
            ),
            discord.Color.green()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        await ctx.send(embed=embed)

    # =========================
    # CONFIG
    # =========================
    @commands.hybrid_command(
        name="welcomeconfig",
        help="View welcome configuration.",
        extras={
            "example": "!welcomeconfig",
            "tips": "Shows current setup."
        }
    )
    async def welcomeconfig(self, ctx):
        """View welcome config."""

        data = self.get_data(ctx.guild.id)

        if not data:

            return await ctx.send(
                "❌ Not configured."
            )

        embed = discord.Embed(
            title="⚙️ Welcome Configuration",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📥 Welcome Channel",
            value=f"<#{data[1]}>" if data[1] else "None",
            inline=False
        )

        embed.add_field(
            name="📤 Leave Channel",
            value=f"<#{data[2]}>" if data[2] else "None",
            inline=False
        )

        embed.add_field(
            name="👋 Welcome Message",
            value=data[3] or "None",
            inline=False
        )

        embed.add_field(
            name="💔 Leave Message",
            value=data[4] or "None",
            inline=False
        )

        await ctx.send(embed=embed)


# =========================
# SETUP
# =========================
async def setup(bot):

    await bot.add_cog(Welcome(bot))
