import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import time
from utils.logger import save_log

DB_PATH = "bot.db"
BRAND_COLOR = 0x2b2d31

# Module Choices
ACTIONS = [
    app_commands.Choice(name="Banning Members", value="ban"),
    app_commands.Choice(name="Kicking Members", value="kick"),
    app_commands.Choice(name="Deleting Roles", value="role_delete"),
    app_commands.Choice(name="Creating Roles", value="role_create"),
    app_commands.Choice(name="Deleting Channels", value="channel_delete"),
    app_commands.Choice(name="Creating Channels", value="channel_create"),
]

# Strict Limits (Actions per 10 seconds)
LIMITS = {
    "ban": 3, "kick": 3, "role_delete": 2, "role_create": 2,
    "channel_delete": 2, "channel_create": 2
}

TIME_WINDOW = 10

class ModPanel(discord.ui.View):
    def __init__(self, target_member: discord.Member, moderator: discord.Member):
        super().__init__(timeout=120)
        self.target = target_member
        self.moderator = moderator

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.moderator:
            await interaction.response.send_message("❌ This panel is not for you!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Quarantine", style=discord.ButtonStyle.red, emoji="🛡️")
    async def quarantine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.target.edit(roles=[], reason="Anti-Nuke Quarantine")
            await interaction.response.send_message(f"🛡️ **{self.target.name}** quarantined.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Permission Error.", ephemeral=True)

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.gray, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.target.ban(reason=f"Emergency Panel Ban by {interaction.user}")
            await interaction.response.send_message(f"🔨 Banned **{self.target.name}**.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Failed to ban.", ephemeral=True)

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.action_tracker = {} # {(guild_id, user_id, action): [timestamps]}

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS antinuke_settings (guild_id INTEGER, action TEXT, enabled INTEGER, PRIMARY KEY (guild_id, action))")
            await db.execute("CREATE TABLE IF NOT EXISTS whitelist (guild_id INTEGER, user_id INTEGER, PRIMARY KEY (guild_id, user_id))")
            await db.commit()

    # =========================
    # LOGIC HELPERS
    # =========================
    async def is_enabled(self, gid, action):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT enabled FROM antinuke_settings WHERE guild_id=? AND action=?", (gid, action)) as cursor:
                r = await cursor.fetchone()
                return r is None or r[0] == 1

    async def is_whitelisted(self, gid, uid):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM whitelist WHERE guild_id=? AND user_id=?", (gid, uid)) as cursor:
                return await cursor.fetchone() is not None

    def check_limit(self, gid, uid, action):
        now = time.time()
        key = (gid, uid, action)
        self.action_tracker.setdefault(key, [])
        self.action_tracker[key] = [t for t in self.action_tracker[key] if now - t < TIME_WINDOW]
        self.action_tracker[key].append(now)
        return len(self.action_tracker[key])

    async def punish(self, guild, user, reason):
        """The 'famous' hammer: Bans the admin and logs it."""
        try:
            await guild.ban(user, reason=f"Anti-Nuke: {reason}")
            save_log(guild.id, 0, "antinuke", f"🚨 Banned {user} for {reason}")
        except:
            pass

    # =========================
    # LISTENERS (PROTECTION)
    # =========================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        if not await self.is_enabled(guild.id, "channel_delete"): return

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.user.id == self.bot.user.id or await self.is_whitelisted(guild.id, entry.user.id): return
            
            # Auto-Recovery
            await channel.clone(reason="Anti-Nuke: Auto-Recovery")
            
            if self.check_limit(guild.id, entry.user.id, "channel_delete") >= LIMITS["channel_delete"]:
                await self.punish(guild, entry.user, "Mass Channel Deletion")

    # =========================
    # HYBRID COMMANDS
    # =========================
    @commands.hybrid_command(name="enable", description="🛡️ Enable an anti-nuke module.")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(action="Module to enable")
    @app_commands.choices(action=ACTIONS)
    async def enable(self, ctx, action: app_commands.Choice[str]):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO antinuke_settings VALUES (?, ?, 1)", (ctx.guild.id, action.value))
            await db.commit()
        await ctx.send(embed=discord.Embed(description=f"✅ **{action.name}** enabled.", color=discord.Color.green()))

    @commands.hybrid_command(name="disable", description="❌ Disable an anti-nuke module.")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(action="Module to disable")
    @app_commands.choices(action=ACTIONS)
    async def disable(self, ctx, action: app_commands.Choice[str]):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO antinuke_settings VALUES (?, ?, 0)", (ctx.guild.id, action.value))
            await db.commit()
        await ctx.send(embed=discord.Embed(description=f"❌ **{action.name}** disabled.", color=discord.Color.red()))

    @commands.hybrid_command(name="whitelist_add", description="🛡️ Trust a user to bypass Anti-Nuke.")
    @commands.has_permissions(administrator=True)
    async def whitelist_add(self, ctx, user: discord.Member):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO whitelist VALUES (?, ?)", (ctx.guild.id, user.id))
            await db.commit()
        await ctx.send(f"✅ {user.mention} is now whitelisted.")

    @commands.hybrid_command(name="antinuke_panel", description="⚖️ Open emergency mod panel.")
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(member="Member to manage")
    async def panel(self, ctx, member: discord.Member):
        embed = discord.Embed(title="🛡️ Security Panel", description=f"Managing: {member.mention}", color=BRAND_COLOR)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed, view=ModPanel(member, ctx.author))

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
