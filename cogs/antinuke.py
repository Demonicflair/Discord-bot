import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import time

# Leaving your logger intact
from utils.logger import get_logs, save_log, is_log_enabled

# Pointing to our central asynchronous database
DB_PATH = "bot.db"

# =========================
# ACTIONS & LIMITS
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
    "ban": 3, "kick": 3, "role_delete": 2, "role_create": 2,
    "channel_delete": 2, "channel_create": 2, "dangerous_role": 1, "dangerous_perm": 1
}

TIME_WINDOW = 10

# =========================
# PRO MOD PANEL (Interactive UI)
# =========================
class ModPanel(discord.ui.View):
    def __init__(self, target_member: discord.Member, moderator: discord.Member):
        super().__init__(timeout=120) # Times out after 2 mins to save memory
        self.target = target_member
        self.moderator = moderator

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.moderator:
            await interaction.response.send_message("❌ This panel is not for you!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Quarantine", style=discord.ButtonStyle.red, emoji="🛡️")
    async def quarantine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Strips all roles to stop a nuke instantly
        try:
            await self.target.edit(roles=[])
            await interaction.response.send_message(f"🛡️ **{self.target.name}** has been quarantined (all roles removed).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("❌ Could not quarantine. Is my role high enough?", ephemeral=True)

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.gray, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.target.ban(reason=f"Panel Ban by {interaction.user}")
            await interaction.response.send_message(f"🔨 Banned **{self.target.name}**.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Failed to ban. Check my permissions.", ephemeral=True)


# =========================
# COG
# =========================
class AntiNuke(commands.Cog):
    """
    🛡️ Advanced Anti-Nuke System
    Protects the server from rogue admins, raids, and mass deletions.
    """
    def __init__(self, bot):
        self.bot = bot
        self.actions = {}

    async def cog_load(self):
        """Initializes tables asynchronously when the cog loads."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS antinuke_settings (guild_id INTEGER, action TEXT, enabled INTEGER, PRIMARY KEY (guild_id, action))")
            await db.execute("CREATE TABLE IF NOT EXISTS antinuke_punish (guild_id INTEGER, user_id INTEGER, count INTEGER, PRIMARY KEY (guild_id, user_id))")
            await db.commit()

    # =========================
    # HELPERS
    # =========================
    async def is_enabled(self, gid, action):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT enabled FROM antinuke_settings WHERE guild_id=? AND action=?", (gid, action)) as cursor:
                r = await cursor.fetchone()
                return r is None or r[0] == 1

    async def is_whitelisted(self, gid, uid):
        # Checks the central whitelist we made in database.py
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM whitelist WHERE guild_id=? AND user_id=?", (gid, uid)) as cursor:
                return await cursor.fetchone() is not None

    def track(self, uid, action):
        now = time.time()
        key = (uid, action)
        self.actions.setdefault(key, []).append(now)
        self.actions[key] = [t for t in self.actions[key] if now - t < TIME_WINDOW]
        return len(self.actions[key])

    # =========================
    # AUTO-RECOVERY & CHECKS
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        # 1. Advanced Recovery: Clone instead of creating blank
        try:
            await channel.clone(name=channel.name, reason="AntiNuke: Channel Auto-Recovery")
        except:
            pass

        # 2. Log & Check
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.user.bot: return
            whitelisted = await self.is_whitelisted(channel.guild.id, entry.user.id)
            if whitelisted: return

            count = self.track(entry.user.id, "channel_delete")
            if count >= LIMITS["channel_delete"]:
                await self.punish(channel.guild, entry.user, "Mass Channel Deletion")

    # =========================
    # COMMANDS (Secured & Styled)
    # =========================
    @commands.hybrid_command(name="enable", description="🛡️ Enable a specific anti-nuke module.")
    @commands.has_permissions(administrator=True) # SECURITY FIX
    @app_commands.choices(action=ACTIONS)
    async def enable(self, ctx, action: app_commands.Choice[str]):
        """Enable a protection module (Admins Only)."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO antinuke_settings VALUES (?, ?, 1)", (ctx.guild.id, action.value))
            await db.commit()

        embed = discord.Embed(title="🛡️ Anti-Nuke Updated", description=f"**{action.name}** protection is now `ENABLED`.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="whitelist_add", description="🛡️ Whitelist a trusted admin from Anti-Nuke triggers.")
    @commands.has_permissions(administrator=True) # SECURITY FIX
    async def whitelist_add(self, ctx, user: discord.Member):
        """Add a user to the whitelist (Admins Only)."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO whitelist VALUES (?, ?)", (ctx.guild.id, user.id))
            await db.commit()

        embed = discord.Embed(description=f"✅ {user.mention} is now **whitelisted** and bypasses Anti-Nuke.", color=0x2b2d31)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="panel", description="⚖️ Open the advanced moderation panel for a user.")
    @commands.has_permissions(manage_messages=True)
    async def panel(self, ctx, member: discord.Member):
        """Open an interactive moderation UI (Mods Only)."""
        embed = discord.Embed(
            title="⚖️ Moderation Control Panel",
            description=f"**Target User:** {member.mention}\n**ID:** `{member.id}`\n\nSelect an action below.",
            color=0x2b2d31 # Pro Discord aesthetic color
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await ctx.send(embed=embed, view=ModPanel(target_member=member, moderator=ctx.author))

    # Error handler for the missing permissions
    @enable.error
    @whitelist_add.error
    @panel.error
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(description="❌ You lack the permissions to use this command.", color=discord.Color.red()), ephemeral=True)

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
