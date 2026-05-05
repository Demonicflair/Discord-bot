import discord
from discord.ext import commands
from discord import app_commands
import sqlite3, time

db = sqlite3.connect("antinuke.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS whitelist(guild_id INTEGER, user_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS logs(guild_id INTEGER, channel_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS punish(guild_id INTEGER, user_id INTEGER, count INTEGER)")
db.commit()

LIMITS = {"danger": 1}
TIME_WINDOW = 10

class Panel(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.red)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.member.ban(reason="Panel ban")
        await interaction.response.send_message("User banned", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.gray)
    async def kick(self, interaction, button):
        await self.member.kick(reason="Panel kick")
        await interaction.response.send_message("User kicked", ephemeral=True)

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.actions = {}

    # =========================
    # UTIL
    # =========================
    def is_whitelisted(self, gid, uid):
        cursor.execute("SELECT * FROM whitelist WHERE guild_id=? AND user_id=?", (gid, uid))
        return cursor.fetchone() is not None

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
    # DANGEROUS DETECTION
    # =========================
    def dangerous(self, role):
        return role.permissions.administrator or role.permissions.manage_guild

    # =========================
    # EVENTS
    # =========================
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if before.permissions != after.permissions and self.dangerous(after):
            await after.edit(permissions=before.permissions)
            await self.log(after.guild, f"⚠️ Dangerous perms reverted in {after.name}")

            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
                await self.punish(after.guild, entry.user, "danger_perm")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await channel.guild.create_text_channel(channel.name)
        await self.log(channel.guild, f"♻️ Channel restored: {channel.name}")

    # =========================
    # COMMANDS
    # =========================
    @commands.hybrid_command()
    async def panel(self, ctx, member: discord.Member=None):
        if not member:
            return await ctx.send("❌ Usage: /panel <user>")
        await ctx.send("Moderation Panel:", view=Panel(member))

    @commands.hybrid_command()
    async def whitelist_add(self, ctx, user: discord.Member=None):
        if not user:
            return await ctx.send("❌ Usage: /whitelist_add <user>")
        cursor.execute("INSERT INTO whitelist VALUES (?,?)",(ctx.guild.id,user.id))
        db.commit()
        await ctx.send("Added")

    @commands.hybrid_command()
    async def whitelist_remove(self, ctx, user: discord.Member=None):
        if not user:
            return await ctx.send("❌ Usage: /whitelist_remove <user>")
        cursor.execute("DELETE FROM whitelist WHERE guild_id=? AND user_id=?",(ctx.guild.id,user.id))
        db.commit()
        await ctx.send("Removed")

    @commands.hybrid_command()
    async def setlog(self, ctx, channel: discord.TextChannel=None):
        if not channel:
            return await ctx.send("❌ Usage: /setlog <channel>")
        cursor.execute("DELETE FROM logs WHERE guild_id=?", (ctx.guild.id,))
        cursor.execute("INSERT INTO logs VALUES (?,?)",(ctx.guild.id,channel.id))
        db.commit()
        await ctx.send("Log set")

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
