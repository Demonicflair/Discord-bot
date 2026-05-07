import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import time

from utils.logger import get_logs, save_log, is_log_enabled

db = sqlite3.connect("antinuke.db", check_same_thread=False)
cursor = db.cursor()

# =========================
# DATABASE
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings(
    guild_id INTEGER,
    action TEXT,
    enabled INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS whitelist(
    guild_id INTEGER,
    user_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS punish(
    guild_id INTEGER,
    user_id INTEGER,
    count INTEGER
)
""")

db.commit()

# =========================
# ACTIONS
# =========================
ACTIONS = [
    app_commands.Choice(name="Banning Members", value="ban"),
    app_commands.Choice(name="Kicking Members", value="kick"),
    app_commands.Choice(name="Deleting Roles", value="role_delete"),
    app_commands.Choice(name="Creating Roles", value="role_create"),
    app_commands.Choice(name="Deleting Channels", value="channel_delete"),
    app_commands.Choice(name="Creating Channels", value="channel_create"),
    app_commands.Choice(name="Dangerous Roles", value="dangerous_role"),
    app_commands.Choice(name="Dangerous Permissions", value="dangerous_perm"),
]

LIMITS = {
    "ban": 3,
    "kick": 3,
    "role_delete": 2,
    "role_create": 2,
    "channel_delete": 2,
    "channel_create": 2,
    "dangerous_role": 1,
    "dangerous_perm": 1
}

TIME_WINDOW = 10


# =========================
# MOD PANEL
# =========================
class Panel(discord.ui.View):

    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.red)
    async def ban_button(self, interaction: discord.Interaction, button):

        await self.member.ban(reason=f"Panel Ban by {interaction.user}")

        await interaction.response.send_message(
            f"🔨 Banned {self.member}",
            ephemeral=True
        )

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.gray)
    async def kick_button(self, interaction: discord.Interaction, button):

        await self.member.kick(reason=f"Panel Kick by {interaction.user}")

        await interaction.response.send_message(
            f"👢 Kicked {self.member}",
            ephemeral=True
        )


# =========================
# COG
# =========================
class AntiNuke(commands.Cog):
    """
    Advanced anti-nuke protection system.
    Protects server from raids, dangerous permissions,
    role/channel nukes and mass moderation abuse.
    """

    def __init__(self, bot):
        self.bot = bot
        self.actions = {}

    # =========================
    # SETTINGS
    # =========================
    def set_enabled(self, gid, action, state):

        cursor.execute(
            "DELETE FROM settings WHERE guild_id=? AND action=?",
            (gid, action)
        )

        cursor.execute(
            "INSERT INTO settings VALUES (?, ?, ?)",
            (gid, action, int(state))
        )

        db.commit()

    def is_enabled(self, gid, action):

        cursor.execute(
            "SELECT enabled FROM settings WHERE guild_id=? AND action=?",
            (gid, action)
        )

        r = cursor.fetchone()

        return r is None or r[0] == 1

    def is_whitelisted(self, gid, uid):

        cursor.execute(
            "SELECT * FROM whitelist WHERE guild_id=? AND user_id=?",
            (gid, uid)
        )

        return cursor.fetchone() is not None

    # =========================
    # LOG SYSTEM
    # =========================
    async def send_log(self, guild, log_type, text):

        logs = get_logs(guild.id)

        if logs and is_log_enabled(guild.id, log_type):

            channel = guild.get_channel(logs[1])

            if channel:

                embed = discord.Embed(
                    description=text,
                    color=discord.Color.red()
                )

                embed.set_footer(text="AntiNuke System")

                await channel.send(embed=embed)

        save_log(guild.id, 0, log_type, text)

    # =========================
    # SMART PUNISH
    # =========================
    async def punish(self, guild, user, reason):

        if self.is_whitelisted(guild.id, user.id):
            return

        member = guild.get_member(user.id)

        if not member:
            return

        cursor.execute(
            "SELECT count FROM punish WHERE guild_id=? AND user_id=?",
            (guild.id, user.id)
        )

        r = cursor.fetchone()

        count = (r[0] + 1) if r else 1

        cursor.execute(
            "DELETE FROM punish WHERE guild_id=? AND user_id=?",
            (guild.id, user.id)
        )

        cursor.execute(
            "INSERT INTO punish VALUES (?, ?, ?)",
            (guild.id, user.id, count)
        )

        db.commit()

        if count == 1:

            await self.send_log(
                guild,
                "antinuke",
                f"⚠️ Warned {member} | {reason}"
            )

        elif count == 2:

            await member.kick(reason=reason)

            await self.send_log(
                guild,
                "antinuke",
                f"👢 Kicked {member} | {reason}"
            )

        else:

            await member.ban(reason=reason)

            await self.send_log(
                guild,
                "antinuke",
                f"🔨 Banned {member} | {reason}"
            )

    # =========================
    # TRACK ACTIONS
    # =========================
    def track(self, uid, action):

        now = time.time()

        key = (uid, action)

        self.actions.setdefault(key, []).append(now)

        self.actions[key] = [
            t for t in self.actions[key]
            if now - t < TIME_WINDOW
        ]

        return len(self.actions[key])

    # =========================
    # DANGEROUS ROLE CHECK
    # =========================
    def dangerous(self, role):

        dangerous_perms = [
            role.permissions.administrator,
            role.permissions.manage_guild,
            role.permissions.manage_roles,
            role.permissions.ban_members,
            role.permissions.kick_members
        ]

        return any(dangerous_perms)

    # =========================
    # CHECK SYSTEM
    # =========================
    async def check(self, guild, action, audit):

        if not self.is_enabled(guild.id, action):
            return

        async for entry in guild.audit_logs(limit=1, action=audit):

            user = entry.user

            if user.bot:
                return

            if self.is_whitelisted(guild.id, user.id):
                return

            count = self.track(user.id, action)

            if count >= LIMITS[action]:

                await self.send_log(
                    guild,
                    "antinuke",
                    f"💣 {user} exceeded {action} limit ({count})"
                )

                await self.punish(guild, user, action)

    # =========================
    # EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):

        try:
            await role.guild.create_role(name=role.name)
        except:
            pass

        await self.send_log(
            role.guild,
            "antinuke",
            f"⚠️ Role deleted: `{role.name}`"
        )

        await self.check(
            role.guild,
            "role_delete",
            discord.AuditLogAction.role_delete
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        try:
            await channel.guild.create_text_channel(channel.name)
        except:
            pass

        await self.send_log(
            channel.guild,
            "antinuke",
            f"⚠️ Channel deleted: `{channel.name}`"
        )

        await self.check(
            channel.guild,
            "channel_delete",
            discord.AuditLogAction.channel_delete
        )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):

        if before.permissions != after.permissions:

            if self.dangerous(after):

                try:
                    await after.edit(
                        permissions=before.permissions
                    )
                except:
                    pass

                await self.send_log(
                    after.guild,
                    "antinuke",
                    f"⚠️ Dangerous permissions detected on `{after.name}`"
                )

                await self.check(
                    after.guild,
                    "dangerous_perm",
                    discord.AuditLogAction.role_update
                )

    # =========================
    # ENABLE
    # =========================
    @commands.hybrid_command(
        name="enable",
        description="Enable a specific antinuke protection"
    )
    @app_commands.describe(
        action="Protection module to enable"
    )
    @app_commands.choices(action=ACTIONS)
    async def enable(self, ctx, action: app_commands.Choice[str]):
        """
        Enable a specific anti-nuke protection module.

        Example:
        !enable role_delete
        /enable role_delete
        """

        self.set_enabled(ctx.guild.id, action.value, True)

        embed = discord.Embed(
            description=f"✅ Enabled `{action.name}`",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    # =========================
    # DISABLE
    # =========================
    @commands.hybrid_command(
        name="disable",
        description="Disable a specific antinuke protection"
    )
    @app_commands.describe(
        action="Protection module to disable"
    )
    @app_commands.choices(action=ACTIONS)
    async def disable(self, ctx, action: app_commands.Choice[str]):
        """
        Disable a specific anti-nuke protection module.

        Example:
        !disable role_delete
        /disable role_delete
        """

        self.set_enabled(ctx.guild.id, action.value, False)

        embed = discord.Embed(
            description=f"❌ Disabled `{action.name}`",
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)

    # =========================
    # WHITELIST ADD
    # =========================
    @commands.hybrid_command(
        name="whitelist_add",
        description="Add a user to antinuke whitelist"
    )
    async def whitelist_add(self, ctx, user: discord.Member = None):
        """
        Add a user to the antinuke whitelist.

        Syntax:
        !whitelist_add @user
        """

        if not user:
            return await ctx.send(
                "❌ Usage: `!whitelist_add @user`"
            )

        cursor.execute(
            "INSERT INTO whitelist VALUES (?, ?)",
            (ctx.guild.id, user.id)
        )

        db.commit()

        await ctx.send(f"✅ Added {user.mention}")

    # =========================
    # WHITELIST REMOVE
    # =========================
    @commands.hybrid_command(
        name="whitelist_remove",
        description="Remove a user from antinuke whitelist"
    )
    async def whitelist_remove(self, ctx, user: discord.Member = None):
        """
        Remove a user from whitelist.

        Syntax:
        !whitelist_remove @user
        """

        if not user:
            return await ctx.send(
                "❌ Usage: `!whitelist_remove @user`"
            )

        cursor.execute(
            "DELETE FROM whitelist WHERE guild_id=? AND user_id=?",
            (ctx.guild.id, user.id)
        )

        db.commit()

        await ctx.send(f"❌ Removed {user.mention}")

    # =========================
    # PANEL
    # =========================
    @commands.hybrid_command(
        name="panel",
        description="Open moderation action panel"
    )
    async def panel(self, ctx, member: discord.Member = None):
        """
        Open a moderation panel.

        Syntax:
        !panel @user
        """

        if not member:
            return await ctx.send(
                "❌ Usage: `!panel @user`"
            )

        embed = discord.Embed(
            title="🛠️ Moderation Panel",
            description=f"Target: {member.mention}",
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed, view=Panel(member))


async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
