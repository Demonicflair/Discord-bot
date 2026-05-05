import discord
from discord.ext import commands
import time

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.joins = {}
        self.messages = {}

    # =========================
    # ANTI RAID
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        now = time.time()
        gid = member.guild.id

        self.joins.setdefault(gid, []).append(now)
        self.joins[gid] = [t for t in self.joins[gid] if now - t < 10]

        if len(self.joins[gid]) >= 5:
            await self.lockdown(member.guild)

    # =========================
    # SPAM DETECTION
    # =========================
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        uid = message.author.id
        now = time.time()

        self.messages.setdefault(uid, []).append(now)
        self.messages[uid] = [t for t in self.messages[uid] if now - t < 5]

        if len(self.messages[uid]) >= 6:
            try:
                await message.author.timeout(discord.utils.utcnow() + discord.timedelta(seconds=30))
                await message.channel.send(f"{message.author.mention} muted for spam")
            except:
                pass

    # =========================
    # LOCKDOWN
    # =========================
    async def lockdown(self, guild):
        for ch in guild.text_channels:
            try:
                await ch.set_permissions(guild.default_role, send_messages=False)
            except:
                pass

    async def unlock(self, guild):
        for ch in guild.text_channels:
            try:
                await ch.set_permissions(guild.default_role, send_messages=True)
            except:
                pass

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
