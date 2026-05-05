import discord
from discord.ext import commands
from discord import app_commands
import sqlite3, time

db = sqlite3.connect("antinuke.db", check_same_thread=False)
cursor = db.cursor()

# =========================
# DATABASE
# =========================
cursor.execute("CREATE TABLE IF NOT EXISTS settings(guild_id INTEGER, action TEXT, enabled INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS whitelist(guild_id INTEGER, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS punish(guild_id INTEGER, user_id INTEGER, count INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS logs(guild_id INTEGER, channel_id INTEGER)")
db.commit()

# =========================
# ACTIONS (DROPDOWN)
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


class Panel(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.red)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.ban()
        await interaction.response.send_message("🔨 Banned", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.gray)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.kick()
        await interaction.response.send_message("👢 Kicked", ephemeral=True)


class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.actions = {}

    # =========================
    # SETTINGS
    # =========================
    def set_enabled(self, gid, action, state):
        cursor.execute("DELETE FROM settings WHERE guild_id=? AND action=?", (gid, action))
        cursor.execute("INSERT INTO settings VALUES (?, ?, ?)", (gid, action, int(state)))
        db.commit()

    def is_enabled(self, gid, action):
        cursor.execute("SELECT enabled FROM settings WHERE guild_id=? AND action=?", (gid, action))
        r = cursor.fetchone()
        return r is None or r[0] == 1

    def is_whitelisted(self, gid, uid):
        cursor.execute("SELECT * FROM whitelist WHERE guild_id=? AND user_id=?", (gid, uid))
        return cursor.fetchone() is not None

    # =========================
    # LOGGING
    # =========================
    async def log(self, guild, text):
        cursor.execute("SELECT channel_id FROM logs WHERE guild_id=?", (guild.id,))
        r = cursor.fetchone()
        if not r:
            return

        ch = guild.get_channel(r[0])
        if ch:
            embed = discord.Embed(description=text, color=discord.Color.red())
            await ch.send(embed=embed)

    # =========================
    # SMART PUNISH
    # =========================
    async def punish(self, guild, user, reason):
        if self.is_whitelisted(guild.id, user.id):
            return

        member = guild.get_member(user.id)
        if not member:
            return

        cursor.execute("SELECT count FROM punish WHERE guild_id=? AND user_id=?", (guild.id, user.id))
        r = cursor.fetchone()
        count = (r[0] + 1) if r else 1

        cursor.execute("DELETE FROM punish WHERE guild_id=? AND user_id=?", (guild.id, user.id))
        cursor.execute("INSERT INTO punish VALUES (?, ?, ?)", (guild.id, user.id, count))
        db.commit()

        if count == 1:
            await self.log(guild, f"⚠️ Warned {member.mention}")
        elif count == 2:
            await member.kick()
            await self.log(guild, f"👢 Kicked {member.mention}")
        else:
            await member.ban()
            await self.log(guild, f"🔨 Banned {member.mention}")

    # =========================
    # TRACK
    # =========================
    def track(self, uid, action):
        now = time.time()
        key = (uid, action)

        self.actions.setdefault(key, []).append(now)
        self.actions[key] = [t for t in self.actions[key] if now - t < TIME_WINDOW]

        return len(self.actions[key])

    def dangerous(self, role):
        return role.permissions.administrator or role.permissions.manage_guild

    async def check(self, guild, action, audit):
        if not self.is_enabled(guild.id, action):
            return

        async for entry in guild.audit_logs(limit=1, action=audit):
            user = entry.user

            if user.bot or self.is_whitelisted(guild.id, user.id):
                return

            if self.track(user.id, action) >= LIMITS[action]:
                await self.punish(guild, user, action)

    # =========================
    # EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await role.guild.create_role(name=role.name)
        await self.check(role.guild, "role_delete", discord.AuditLogAction.role_delete)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await channel.guild.create_text_channel(channel.name)
        await self.check(channel.guild, "channel_delete", discord.AuditLogAction.channel_delete)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if before.permissions != after.permissions and self.dangerous(after):
            await after.edit(permissions=before.permissions)
            await self.check(after.guild, "dangerous_perm", discord.AuditLogAction.role_update)

    # =========================
    # COMMANDS
    # =========================
    @commands.hybrid_command(name="enable")
    @app_commands.describe(action="Select an action to enable")
    @app_commands.choices(action=ACTIONS)
    async def enable(self, ctx, action: app_commands.Choice[str]):
        self.set_enabled(ctx.guild.id, action.value, True)
        await ctx.send(f"✅ Enabled {action.name}")

    @commands.hybrid_command(name="disable")
    @app_commands.describe(action="Select an action to disable")
    @app_commands.choices(action=ACTIONS)
    async def disable(self, ctx, action: app_commands.Choice[str]):
        self.set_enabled(ctx.guild.id, action.value, False)
        await ctx.send(f"❌ Disabled {action.name}")

    @commands.hybrid_command()
    async def whitelist_add(self, ctx, user: discord.Member=None):
        if not user:
            return await ctx.send("❌ Usage: /whitelist_add <user>")
        cursor.execute("INSERT INTO whitelist VALUES (?,?)",(ctx.guild.id,user.id))
        db.commit()
        await ctx.send("✅ Added")

    @commands.hybrid_command()
    async def whitelist_remove(self, ctx, user: discord.Member=None):
        if not user:
            return await ctx.send("❌ Usage: /whitelist_remove <user>")
        cursor.execute("DELETE FROM whitelist WHERE guild_id=? AND user_id=?",(ctx.guild.id,user.id))
        db.commit()
        await ctx.send("❌ Removed")

    @commands.hybrid_command()
    async def setlog(self, ctx, channel: discord.TextChannel=None):
        if not channel:
            return await ctx.send("❌ Usage: /setlog <channel>")
        cursor.execute("DELETE FROM logs WHERE guild_id=?", (ctx.guild.id,))
        cursor.execute("INSERT INTO logs VALUES (?,?)",(ctx.guild.id,channel.id))
        db.commit()
        await ctx.send("📜 Log channel set")

    @commands.hybrid_command()
    async def panel(self, ctx, member: discord.Member=None):
        if not member:
            return await ctx.send("❌ Usage: /panel <user>")
        await ctx.send("Moderation Panel:", view=Panel(member))


async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
