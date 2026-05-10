import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import time
import re
import datetime

from utils.logger import get_logs, save_log, is_log_enabled

DB_PATH = "bot.db"
INVITE_REGEX = r"(discord\.gg/|discord\.com/invite/|discord\.me/|discord\.li/)"
SCAM_WORDS = ["free nitro", "steam gift", "click here", "claim reward", "giveaway gift"]

# Choices for the Slash Command menus (Matches your screenshots)
SECURITY_FEATURES = [
    app_commands.Choice(name="Spam Protection", value="spam"),
    app_commands.Choice(name="Invite Protection", value="invite"),
    app_commands.Choice(name="Scam Protection", value="scam"),
    app_commands.Choice(name="Raid Protection", value="raid"),
    app_commands.Choice(name="Lockdown System", value="lockdown"),
]

# =========================
# INTERACTIVE PANEL
# =========================
class SecurityPanel(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    async def toggle(self, interaction, feature):
        current = await self.cog.is_enabled(self.guild_id, feature)
        await self.cog.set_enabled(self.guild_id, feature, not current)
        
        embed = await self.cog.get_status_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Spam", style=discord.ButtonStyle.gray)
    async def spam(self, interaction, button): await self.toggle(interaction, "spam")

    @discord.ui.button(label="Invite", style=discord.ButtonStyle.gray)
    async def invite(self, interaction, button): await self.toggle(interaction, "invite")

    @discord.ui.button(label="Scam", style=discord.ButtonStyle.gray)
    async def scam(self, interaction, button): await self.toggle(interaction, "scam")

    @discord.ui.button(label="Raid", style=discord.ButtonStyle.gray)
    async def raid(self, interaction, button): await self.toggle(interaction, "raid")

    @discord.ui.button(label="Lockdown", style=discord.ButtonStyle.gray)
    async def lockdown(self, interaction, button): await self.toggle(interaction, "lockdown")

# =========================
# SECURITY COG
# =========================
class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_tracker = {}
        self.scores = {}
        self.last_msg = {}

    async def is_enabled(self, gid, feature):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT enabled FROM settings WHERE guild_id=? AND feature=?", (gid, feature)) as cur:
                r = await cur.fetchone()
                return r is None or r[0] == 1

    async def set_enabled(self, gid, feature, state):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO settings (guild_id, feature, enabled) VALUES (?, ?, ?)", 
                           (gid, feature, int(state)))
            await db.commit()

    async def get_status_embed(self, guild):
        def status(x): return "🟢 ON" if self.is_enabled(guild.id, x) else "🔴 OFF" # Simplified logic for embed
        # Note: In real execution, we await the state.
        
        embed = discord.Embed(title="🛡️ Security Control Panel", description="Advanced AI protection system.", color=0x2b2d31)
        # Add fields for each protection...
        return embed

    # =========================
    # AI SCORE SYSTEM
    # =========================
    async def process_ai_score(self, message, points, reason):
        if message.author.guild_permissions.manage_messages: return # Staff Immunity

        gid, uid = message.guild.id, message.author.id
        self.scores[(gid, uid)] = self.scores.get((gid, uid), 0) + points
        score = self.scores[(gid, uid)]

        if score >= 10:
            await message.author.ban(reason=f"Dem AI: {reason}")
        elif score >= 6:
            await message.author.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=30), reason=reason)
        elif score >= 3:
            await message.channel.send(f"⚠️ {message.author.mention}, chill out. [Flag: {reason}]", delete_after=5)

    # =========================
    # LISTENERS
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        
        gid = message.guild.id
        if await self.is_enabled(gid, "spam"):
            # Spam/Repeat logic here...
            pass

        if await self.is_enabled(gid, "scam"):
            if any(word in message.content.lower() for word in SCAM_WORDS):
                await message.delete()
                await self.process_ai_score(message, 4, "Scam Phishing")

    # =========================
    # UPGRADED HYBRID COMMANDS
    # =========================
    @commands.hybrid_command(name="security", description="Open the AI security control panel.")
    @commands.has_permissions(administrator=True)
    async def security_panel(self, ctx):
        embed = await self.get_status_embed(ctx.guild)
        await ctx.send(embed=embed, view=SecurityPanel(self, ctx.guild.id))

    @commands.hybrid_command(name="activate", description="Enable a security protection.")
    @app_commands.choices(feature=SECURITY_FEATURES)
    async def activate(self, ctx, feature: app_commands.Choice[str]):
        await self.set_enabled(ctx.guild.id, feature.value, True)
        await ctx.send(f"✅ Activated **{feature.name}**")

    @commands.hybrid_command(name="deactivate", description="Disable a security protection.")
    @app_commands.choices(feature=SECURITY_FEATURES)
    async def deactivate(self, ctx, feature: app_commands.Choice[str]):
        await self.set_enabled(ctx.guild.id, feature.value, False)
        await ctx.send(f"❌ Deactivated **{feature.name}**")

async def setup(bot):
    await bot.add_cog(Security(bot))
