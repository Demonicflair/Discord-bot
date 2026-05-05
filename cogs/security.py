import discord
from discord.ext import commands
from discord import app_commands
import time, sqlite3, re

db = sqlite3.connect("security.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS whitelist(guild_id INTEGER, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings(guild_id INTEGER, feature TEXT, enabled INTEGER)")
db.commit()

INVITE_REGEX = r"(discord\.gg/|discord\.com/invite/)"
SCAM_WORDS = ["free nitro", "steam gift", "click here", "claim reward"]

FEATURES = [
    app_commands.Choice(name="Spam Protection", value="spam"),
    app_commands.Choice(name="Invite Protection", value="invite"),
    app_commands.Choice(name="Scam Protection", value="scam"),
    app_commands.Choice(name="Raid Protection", value="raid"),
    app_commands.Choice(name="Lockdown System", value="lockdown"),
]

class SecurityPanel(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id

    async def toggle(self, interaction, feature):
        current = self.cog.is_enabled(self.guild_id, feature)
        self.cog.set_enabled(self.guild_id, feature, not current)

        await interaction.response.edit_message(
            embed=self.cog.get_status_embed(interaction.guild),
            view=SecurityPanel(self.cog, self.guild_id)
        )

    @discord.ui.button(label="Spam", style=discord.ButtonStyle.gray)
    async def spam(self, interaction, button):
        await self.toggle(interaction, "spam")

    @discord.ui.button(label="Invite", style=discord.ButtonStyle.gray)
    async def invite(self, interaction, button):
        await self.toggle(interaction, "invite")

    @discord.ui.button(label="Scam", style=discord.ButtonStyle.gray)
    async def scam(self, interaction, button):
        await self.toggle(interaction, "scam")

    @discord.ui.button(label="Raid", style=discord.ButtonStyle.gray)
    async def raid(self, interaction, button):
        await self.toggle(interaction, "raid")

    @discord.ui.button(label="Lockdown", style=discord.ButtonStyle.gray)
    async def lockdown(self, interaction, button):
        await self.toggle(interaction, "lockdown")


class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.joins = {}
        self.messages = {}
        self.last_message = {}
        self.scores = {}
        self.locked_channels = {}

    # =========================
    # SETTINGS
    # =========================
    def is_enabled(self, gid, feature):
        cursor.execute("SELECT enabled FROM settings WHERE guild_id=? AND feature=?", (gid, feature))
        r = cursor.fetchone()
        return r is None or r[0] == 1

    def set_enabled(self, gid, feature, state):
        cursor.execute("DELETE FROM settings WHERE guild_id=? AND feature=?", (gid, feature))
        cursor.execute("INSERT INTO settings VALUES (?, ?, ?)", (gid, feature, int(state)))
        db.commit()

    # =========================
    # WHITELIST
    # =========================
    def is_whitelisted(self, gid, uid):
        cursor.execute("SELECT * FROM whitelist WHERE guild_id=? AND user_id=?", (gid, uid))
        return cursor.fetchone() is not None

    # =========================
    # UI EMBED
    # =========================
    def get_status_embed(self, guild):
        def status(x):
            return "🟢 ON" if self.is_enabled(guild.id, x) else "🔴 OFF"

        embed = discord.Embed(
            title="🛡️ Security Control Panel",
            color=discord.Color.blurple()
        )

        embed.add_field(name="Spam", value=status("spam"))
        embed.add_field(name="Invite", value=status("invite"))
        embed.add_field(name="Scam", value=status("scam"))
        embed.add_field(name="Raid", value=status("raid"))
        embed.add_field(name="Lockdown", value=status("lockdown"))

        embed.set_footer(text="Click buttons below to toggle systems")
        return embed

    # =========================
    # AI SCORE SYSTEM
    # =========================
    async def add_score(self, message, points, reason):
        user = message.author
        gid = message.guild.id

        if self.is_whitelisted(gid, user.id):
            return

        key = (gid, user.id)
        self.scores[key] = self.scores.get(key, 0) + points
        score = self.scores[key]

        if score >= 10:
            await user.ban(reason=reason)
        elif score >= 7:
            await user.kick(reason=reason)
        elif score >= 4:
            await user.timeout(discord.utils.utcnow() + discord.timedelta(seconds=60))
        elif score >= 2:
            await message.channel.send(f"⚠️ {user.mention} warning: {reason}")

    # =========================
    # RAID
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.is_enabled(member.guild.id, "raid"):
            return

        now = time.time()
        gid = member.guild.id

        if (now - member.created_at.timestamp()) < 60:
            await member.kick(reason="New account raid")
            return

        self.joins.setdefault(gid, []).append(now)
        self.joins[gid] = [t for t in self.joins[gid] if now - t < 10]

        if len(self.joins[gid]) >= 5:
            await self.lockdown(member.guild)

    # =========================
    # MESSAGE AI
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        uid = message.author.id
        now = time.time()

        if self.is_enabled(message.guild.id, "spam"):
            self.messages.setdefault(uid, []).append(now)
            self.messages[uid] = [t for t in self.messages[uid] if now - t < 5]
            if len(self.messages[uid]) >= 6:
                await self.add_score(message, 2, "Spam")

        if uid in self.last_message and self.last_message[uid] == message.content:
            await self.add_score(message, 2, "Repeat spam")

        self.last_message[uid] = message.content

        if self.is_enabled(message.guild.id, "invite"):
            if re.search(INVITE_REGEX, message.content.lower()):
                await self.add_score(message, 3, "Invite spam")

        if self.is_enabled(message.guild.id, "scam"):
            for word in SCAM_WORDS:
                if word in message.content.lower():
                    await self.add_score(message, 4, "Scam message")

        if len(message.mentions) >= 5:
            await self.add_score(message, 3, "Mention spam")

    # =========================
    # LOCKDOWN
    # =========================
    async def lockdown(self, guild):
        if not self.is_enabled(guild.id, "lockdown"):
            return

        self.locked_channels[guild.id] = {}

        for ch in guild.text_channels:
            try:
                perms = ch.overwrites_for(guild.default_role)
                self.locked_channels[guild.id][ch.id] = perms.send_messages
                await ch.set_permissions(guild.default_role, send_messages=False)
            except:
                pass

    async def unlock(self, guild):
        if guild.id not in self.locked_channels:
            return

        for ch in guild.text_channels:
            try:
                old = self.locked_channels[guild.id].get(ch.id, True)
                await ch.set_permissions(guild.default_role, send_messages=old)
            except:
                pass

    # =========================
    # COMMANDS
    # =========================
    @commands.hybrid_command(name="security")
    async def security_panel(self, ctx):
        embed = self.get_status_embed(ctx.guild)
        await ctx.send(embed=embed, view=SecurityPanel(self, ctx.guild.id))

    @commands.hybrid_command(name="activate")
    @app_commands.choices(feature=FEATURES)
    async def activate(self, ctx, feature: app_commands.Choice[str]):
        self.set_enabled(ctx.guild.id, feature.value, True)
        await ctx.send(f"✅ Activated {feature.name}")

    @commands.hybrid_command(name="deactivate")
    @app_commands.choices(feature=FEATURES)
    async def deactivate(self, ctx, feature: app_commands.Choice[str]):
        self.set_enabled(ctx.guild.id, feature.value, False)
        await ctx.send(f"❌ Deactivated {feature.name}")

    @commands.hybrid_command()
    async def lockdown_cmd(self, ctx):
        await self.lockdown(ctx.guild)
        await ctx.send("🔒 Locked")

    @commands.hybrid_command()
    async def unlock_cmd(self, ctx):
        await self.unlock(ctx.guild)
        await ctx.send("🔓 Unlocked")


async def setup(bot):
    await bot.add_cog(Security(bot))
