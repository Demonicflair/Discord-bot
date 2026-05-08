# booster.py

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

from utils.logger import get_logs, save_log, is_log_enabled

# =========================
# DATABASE
# =========================
db = sqlite3.connect("booster.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS booster_roles(
    guild_id INTEGER,
    user_id INTEGER,
    role_id INTEGER
)
""")

db.commit()

# =========================
# LOG SYSTEM
# =========================
async def send_log(guild, text):

    logs = get_logs(guild.id)

    if logs and is_log_enabled(guild.id, "booster"):

        channel = guild.get_channel(logs[1])

        if channel:
            embed = discord.Embed(
                description=text,
                color=discord.Color.purple()
            )

            await channel.send(embed=embed)

    save_log(guild.id, 0, "booster", text)


# =========================
# COG
# =========================
class Booster(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # BOOST ROLE CREATE
    # =========================
    @commands.hybrid_command(
        name="boosterrole",
        help="Create a custom booster role.",
        extras={
            "example": "!boosterrole Red",
            "tips": "Only server boosters can use this."
        }
    )
    async def boosterrole(
        self,
        ctx,
        *,
        name=None
    ):
        """Create booster role."""

        if not ctx.author.premium_since:

            return await ctx.send(
                "❌ You must boost the server."
            )

        if not name:

            return await ctx.send(
                "❌ Usage: !boosterrole <name>"
            )

        cursor.execute(
            """
            SELECT role_id FROM booster_roles
            WHERE guild_id=? AND user_id=?
            """,
            (ctx.guild.id, ctx.author.id)
        )

        existing = cursor.fetchone()

        if existing:

            role = ctx.guild.get_role(existing[0])

            if role:

                return await ctx.send(
                    f"❌ You already have {role.mention}"
                )

        role = await ctx.guild.create_role(
            name=name,
            color=discord.Color.random(),
            reason="Custom Booster Role"
        )

        await ctx.author.add_roles(role)

        cursor.execute(
            "INSERT INTO booster_roles VALUES (?, ?, ?)",
            (ctx.guild.id, ctx.author.id, role.id)
        )

        db.commit()

        embed = discord.Embed(
            title="✨ Booster Role Created",
            description=f"{role.mention}",
            color=role.color
        )

        await ctx.send(embed=embed)

        await send_log(
            ctx.guild,
            f"✨ {ctx.author} created booster role {role.name}"
        )

    # =========================
    # RENAME ROLE
    # =========================
    @commands.hybrid_command(
        name="boostername",
        help="Rename your booster role.",
        extras={
            "example": "!boostername Galaxy",
            "tips": "Changes your custom role name."
        }
    )
    async def boostername(
        self,
        ctx,
        *,
        name=None
    ):
        """Rename booster role."""

        if not name:

            return await ctx.send(
                "❌ Usage: !boostername <name>"
            )

        cursor.execute(
            """
            SELECT role_id FROM booster_roles
            WHERE guild_id=? AND user_id=?
            """,
            (ctx.guild.id, ctx.author.id)
        )

        data = cursor.fetchone()

        if not data:

            return await ctx.send(
                "❌ You do not own a booster role."
            )

        role = ctx.guild.get_role(data[0])

        if not role:

            return await ctx.send(
                "❌ Role not found."
            )

        await role.edit(name=name)

        await ctx.send(
            f"✅ Renamed role to **{name}**"
        )

    # =========================
    # ROLE COLOR
    # =========================
    @commands.hybrid_command(
        name="boostercolor",
        help="Change booster role color.",
        extras={
            "example": "!boostercolor #ff0000",
            "tips": "Use hex colors."
        }
    )
    async def boostercolor(
        self,
        ctx,
        color=None
    ):
        """Change booster role color."""

        if not color:

            return await ctx.send(
                "❌ Usage: !boostercolor <hex>"
            )

        cursor.execute(
            """
            SELECT role_id FROM booster_roles
            WHERE guild_id=? AND user_id=?
            """,
            (ctx.guild.id, ctx.author.id)
        )

        data = cursor.fetchone()

        if not data:

            return await ctx.send(
                "❌ No booster role found."
            )

        role = ctx.guild.get_role(data[0])

        if not role:

            return await ctx.send(
                "❌ Role not found."
            )

        try:

            new_color = discord.Color.from_str(color)

        except:

            return await ctx.send(
                "❌ Invalid hex color."
            )

        await role.edit(color=new_color)

        embed = discord.Embed(
            title="🎨 Booster Role Updated",
            description=f"New color: `{color}`",
            color=new_color
        )

        await ctx.send(embed=embed)

    # =========================
    # DELETE BOOSTER ROLE
    # =========================
    @commands.hybrid_command(
        name="deletebooster",
        help="Delete your booster role.",
        extras={
            "example": "!deletebooster",
            "tips": "Removes your custom role."
        }
    )
    async def deletebooster(self, ctx):
        """Delete booster role."""

        cursor.execute(
            """
            SELECT role_id FROM booster_roles
            WHERE guild_id=? AND user_id=?
            """,
            (ctx.guild.id, ctx.author.id)
        )

        data = cursor.fetchone()

        if not data:

            return await ctx.send(
                "❌ No booster role found."
            )

        role = ctx.guild.get_role(data[0])

        if role:

            await role.delete()

        cursor.execute(
            """
            DELETE FROM booster_roles
            WHERE guild_id=? AND user_id=?
            """,
            (ctx.guild.id, ctx.author.id)
        )

        db.commit()

        await ctx.send(
            "🗑️ Booster role deleted."
        )

    # =========================
    # AUTO REMOVE ON UNBOOST
    # =========================
    @commands.Cog.listener()
    async def on_member_update(self, before, after):

        if before.premium_since and not after.premium_since:

            cursor.execute(
                """
                SELECT role_id FROM booster_roles
                WHERE guild_id=? AND user_id=?
                """,
                (after.guild.id, after.id)
            )

            data = cursor.fetchone()

            if not data:
                return

            role = after.guild.get_role(data[0])

            if role:

                try:
                    await role.delete()

                except:
                    pass

            cursor.execute(
                """
                DELETE FROM booster_roles
                WHERE guild_id=? AND user_id=?
                """,
                (after.guild.id, after.id)
            )

            db.commit()

            await send_log(
                after.guild,
                f"❌ Removed booster role from {after}"
            )


# =========================
# SETUP
# =========================
async def setup(bot):

    await bot.add_cog(Booster(bot))
