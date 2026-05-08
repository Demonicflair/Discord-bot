import discord
from discord.ext import commands
from discord import app_commands
import platform
import datetime
import psutil
import sqlite3

from utils.logger import get_logs, save_log, is_log_enabled

# =========================
# DATABASE
# =========================
db = sqlite3.connect("utility.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS afk(
        user_id INTEGER,
        guild_id INTEGER,
        reason TEXT,
        since INTEGER
    )
    """
)

db.commit()


# =========================
# EMBED HELPER
# =========================
def embed_builder(title, description=None, color=discord.Color.blurple()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )
    return embed


# =========================
# UTILITY COG
# =========================
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # LOG SYSTEM
    # =========================
    async def send_log(self, guild, log_type, text):
        logs = get_logs(guild.id)

        if logs and is_log_enabled(guild.id, log_type):
            channel = guild.get_channel(logs[1])

            if channel:
                embed = embed_builder(
                    "📄 Utility Logs",
                    text,
                    discord.Color.dark_gray()
                )
                await channel.send(embed=embed)

        save_log(guild.id, 0, log_type, text)

    # =========================
    # 🧹 PURGE
    # =========================
    @commands.hybrid_command(
        name="purge",
        help="Delete multiple messages quickly.",
        extras={
            "example": "!purge 20",
            "tips": "Requires Manage Messages permission."
        }
    )
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def purge(self, ctx, amount: int = None):
        """Delete multiple messages."""

        if amount is None:
            return await ctx.send("❌ Usage: !purge <amount>")

        if amount <= 0:
            return await ctx.send("❌ Amount must be greater than 0")

        if amount > 100:
            return await ctx.send("❌ Max purge limit is 100")

        deleted = await ctx.channel.purge(limit=amount + 1)

        embed = embed_builder(
            "🧹 Messages Purged",
            f"Deleted **{len(deleted)-1}** messages.",
            discord.Color.red()
        )

        msg = await ctx.send(embed=embed)

        await self.send_log(
            ctx.guild,
            "purge",
            f"🧹 {ctx.author} purged {len(deleted)-1} messages in #{ctx.channel}"
        )

        await msg.delete(delay=5)

    # =========================
    # 🏓 PING
    # =========================
    @commands.hybrid_command(
        name="ping",
        help="Check bot latency.",
        extras={
            "example": "!ping",
            "tips": "Lower ping = faster response speed."
        }
    )
    async def ping(self, ctx):
        """Check bot ping."""

        latency = round(self.bot.latency * 1000)

        if latency < 100:
            status = "🟢 Excellent"
        elif latency < 200:
            status = "🟡 Good"
        else:
            status = "🔴 Slow"

        embed = embed_builder(
            "🏓 Pong!",
            f"**Latency:** `{latency}ms`\n**Status:** {status}",
            discord.Color.green()
        )

        await ctx.send(embed=embed)

    # =========================
    # 🖼️ AVATAR
    # =========================
    @commands.hybrid_command(
        name="avatar",
        help="View a user's avatar.",
        extras={
            "example": "!avatar @user",
            "tips": "Works with any member."
        }
    )
    async def avatar(self, ctx, member: discord.Member = None):
        """View user avatar."""

        member = member or ctx.author

        embed = embed_builder(
            f"🖼️ {member.name}'s Avatar",
            color=discord.Color.blurple()
        )

        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author}")

        await ctx.send(embed=embed)

    # =========================
    # 🌐 SERVER INFO
    # =========================
    @commands.hybrid_command(
        name="serverinfo",
        help="View information about the server.",
        extras={
            "example": "!serverinfo",
            "tips": "Shows member count and creation date."
        }
    )
    async def serverinfo(self, ctx):
        """Display server information."""

        guild = ctx.guild

        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])

        embed = embed_builder(
            f"🌐 {guild.name}",
            color=discord.Color.blurple()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="👑 Owner", value=str(guild.owner))
        embed.add_field(name="👥 Members", value=str(guild.member_count))
        embed.add_field(name="🤖 Bots", value=str(bots))

        embed.add_field(name="🙋 Humans", value=str(humans))
        embed.add_field(name="💬 Channels", value=str(len(guild.channels)))
        embed.add_field(name="🎭 Roles", value=str(len(guild.roles)))

        embed.add_field(
            name="📅 Created",
            value=f"<t:{int(guild.created_at.timestamp())}:R>",
            inline=False
        )

        await ctx.send(embed=embed)

    # =========================
    # 👤 USER INFO
    # =========================
    @commands.hybrid_command(
        name="userinfo",
        help="View information about a member.",
        extras={
            "example": "!userinfo @user",
            "tips": "Useful for moderation."
        }
    )
    async def userinfo(self, ctx, member: discord.Member = None):
        """Display member info."""

        member = member or ctx.author

        roles = [r.mention for r in member.roles[1:]][:10]

        embed = embed_builder(
            f"👤 {member}",
            color=member.color
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="🆔 ID", value=member.id)
        embed.add_field(name="🤖 Bot", value=member.bot)
        embed.add_field(name="🎨 Nickname", value=member.nick or "None")

        embed.add_field(
            name="📅 Joined",
            value=f"<t:{int(member.joined_at.timestamp())}:R>"
        )

        embed.add_field(
            name="📅 Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:R>"
        )

        embed.add_field(
            name="🎭 Roles",
            value=" ".join(roles) if roles else "None",
            inline=False
        )

        await ctx.send(embed=embed)

    # =========================
    # 🤖 BOT INFO
    # =========================
    @commands.hybrid_command(
        name="botinfo",
        help="View bot statistics.",
        extras={
            "example": "!botinfo",
            "tips": "Shows uptime and memory usage."
        }
    )
    async def botinfo(self, ctx):
        """Display bot statistics."""

        process = psutil.Process()
        memory = process.memory_info().rss / 1024 / 1024

        embed = embed_builder(
            "🤖 Bot Information",
            color=discord.Color.blurple()
        )

        embed.add_field(name="🌐 Servers", value=len(self.bot.guilds))
        embed.add_field(name="👥 Users", value=len(self.bot.users))
        embed.add_field(name="📦 Commands", value=len(self.bot.commands))

        embed.add_field(name="💾 RAM Usage", value=f"{memory:.2f} MB")
        embed.add_field(name="🐍 Python", value=platform.python_version())
        embed.add_field(name="⚙️ Discord.py", value=discord.__version__)

        await ctx.send(embed=embed)

    # =========================
    # ⏰ UPTIME
    # =========================
    @commands.hybrid_command(
        name="uptime",
        help="View bot uptime.",
        extras={
            "example": "!uptime",
            "tips": "Useful for monitoring stability."
        }
    )
    async def uptime(self, ctx):
        """Display uptime."""

        now = discord.utils.utcnow()
        delta = now - self.bot.launch_time

        embed = embed_builder(
            "⏰ Uptime",
            f"Bot has been online for:\n`{str(delta).split('.')[0]}`",
            discord.Color.green()
        )

        await ctx.send(embed=embed)

    # =========================
    # 🎭 ROLE ADD
    # =========================
    @commands.hybrid_command(
        name="roleadd",
        help="Add a role to a member.",
        extras={
            "example": "!roleadd @user Member",
            "tips": "Requires Manage Roles permission."
        }
    )
    @commands.has_permissions(manage_roles=True)
    async def roleadd(self, ctx, member: discord.Member = None, *, role: discord.Role = None):
        """Add a role."""

        if not member or not role:
            return await ctx.send("❌ Usage: !roleadd @user <role>")

        await member.add_roles(role)

        embed = embed_builder(
            "✅ Role Added",
            f"Added {role.mention} to {member.mention}",
            discord.Color.green()
        )

        await ctx.send(embed=embed)

        await self.send_log(
            ctx.guild,
            "roles",
            f"🎭 {ctx.author} added {role.name} to {member}"
        )

    # =========================
    # ❌ ROLE REMOVE
    # =========================
    @commands.hybrid_command(
        name="roleremove",
        help="Remove a role from a member.",
        extras={
            "example": "!roleremove @user Member",
            "tips": "Requires Manage Roles permission."
        }
    )
    @commands.has_permissions(manage_roles=True)
    async def roleremove(self, ctx, member: discord.Member = None, *, role: discord.Role = None):
        """Remove a role."""

        if not member or not role:
            return await ctx.send("❌ Usage: !roleremove @user <role>")

        await member.remove_roles(role)

        embed = embed_builder(
            "❌ Role Removed",
            f"Removed {role.mention} from {member.mention}",
            discord.Color.red()
        )

        await ctx.send(embed=embed)

        await self.send_log(
            ctx.guild,
            "roles",
            f"❌ {ctx.author} removed {role.name} from {member}"
        )

    # =========================
    # 💤 AFK
    # =========================
    @commands.hybrid_command(
        name="afk",
        help="Set your AFK status.",
        extras={
            "example": "!afk sleeping",
            "tips": "Your AFK will remove automatically when you chat again."
        }
    )
    async def afk(self, ctx, *, reason="AFK"):
        """Set AFK status."""

        cursor.execute(
            "DELETE FROM afk WHERE user_id=? AND guild_id=?",
            (ctx.author.id, ctx.guild.id)
        )

        cursor.execute(
            "INSERT INTO afk VALUES (?, ?, ?, ?)",
            (
                ctx.author.id,
                ctx.guild.id,
                reason,
                int(discord.utils.utcnow().timestamp())
            )
        )

        db.commit()

        embed = embed_builder(
            "💤 AFK Enabled",
            f"Reason: **{reason}**",
            discord.Color.orange()
        )

        await ctx.send(embed=embed)

    # =========================
    # AFK LISTENER
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot or not message.guild:
            return

        # REMOVE AFK
        cursor.execute(
            "SELECT * FROM afk WHERE user_id=? AND guild_id=?",
            (message.author.id, message.guild.id)
        )

        afk = cursor.fetchone()

        if afk:
            cursor.execute(
                "DELETE FROM afk WHERE user_id=? AND guild_id=?",
                (message.author.id, message.guild.id)
            )

            db.commit()

            embed = embed_builder(
                "👋 Welcome Back",
                "Your AFK status has been removed.",
                discord.Color.green()
            )

            await message.channel.send(embed=embed, delete_after=5)

        # MENTION AFK
        for user in message.mentions:

            cursor.execute(
                "SELECT reason, since FROM afk WHERE user_id=? AND guild_id=?",
                (user.id, message.guild.id)
            )

            result = cursor.fetchone()

            if result:
                reason, since = result

                embed = embed_builder(
                    "💤 User AFK",
                    (
                        f"{user.mention} is AFK\n\n"
                        f"**Reason:** {reason}\n"
                        f"**Since:** <t:{since}:R>"
                    ),
                    discord.Color.orange()
                )

                await message.channel.send(embed=embed)

        await self.bot.process_commands(message)


async def setup(bot):
    await bot.add_cog(Utility(bot))
