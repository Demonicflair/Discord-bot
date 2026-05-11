import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
import asyncio
import random
import time
import datetime

DB_PATH = "bot.db"
BRAND_COLOR = 0x2b2d31

# =========================
# PERSISTENT GIVEAWAY BUTTON
# =========================
class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Join Giveaway",
        emoji="🎉",
        style=discord.ButtonStyle.blurple,
        custom_id="dem:giveaway:join"
    )
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT req_role, black_role FROM giveaways WHERE message_id=?", (interaction.message.id,)) as cur:
                data = await cur.fetchone()
        
        if not data: return

        req_role_id, black_role_id = data[0], data[1]

        # 1. Check Blacklist
        if black_role_id and interaction.user.get_role(black_role_id):
            return await interaction.response.send_message("❌ You have a blacklisted role and cannot join.", ephemeral=True)

        # 2. Check Requirement
        if req_role_id and not interaction.user.get_role(req_role_id):
            role = interaction.guild.get_role(req_role_id)
            return await interaction.response.send_message(f"❌ You need the {role.mention} role to join!", ephemeral=True)

        # 3. Add Entry
        message = interaction.message
        users = [user async for user in message.reactions[0].users()] if message.reactions else []
        
        if interaction.user in users:
            return await interaction.response.send_message("❌ You already joined!", ephemeral=True)
            
        await message.add_reaction("🎉")
        await interaction.response.send_message("✅ Success! You are now entered.", ephemeral=True)

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_loop.start()

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    prize TEXT,
                    winners INTEGER,
                    end_time INTEGER,
                    ended INTEGER DEFAULT 0,
                    req_role INTEGER,
                    black_role INTEGER
                )
            """)
            await db.commit()

    def parse_time(self, time_str):
        time_dict = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = time_str[-1]
        try:
            val = int(time_str[:-1])
            return val * time_dict[unit]
        except: return None

    @tasks.loop(seconds=10)
    async def giveaway_loop(self):
        now = int(time.time())
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM giveaways WHERE ended=0 AND end_time <= ?", (now,)) as cursor:
                ended_giveaways = await cursor.fetchall()
        for g in ended_giveaways:
            await self.end_g(g)

    async def end_g(self, data):
        msg_id, guild_id, chan_id, prize, w_count = data[0], data[1], data[2], data[3], data[4]
        guild = self.bot.get_guild(guild_id)
        if not guild: return
        channel = guild.get_channel(chan_id)
        if not channel: return

        try:
            message = await channel.fetch_message(msg_id)
            users = [u async for u in message.reactions[0].users() if not u.bot]
        except: return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE giveaways SET ended=1 WHERE message_id=?", (msg_id,))
            await db.commit()

        if not users:
            return await channel.send(f"⚠️ No winners for **{prize}** (No entries).")

        winners = random.sample(users, min(len(users), w_count))
        mentions = ", ".join(w.mention for w in winners)

        # Notify Winners in DM
        for w in winners:
            try: await w.send(f"🎉 **Congratulations!** You won **{prize}** in **{guild.name}**!")
            except: pass

        embed = discord.Embed(title="🎁 Giveaway Ended!", description=f"**Prize:** {prize}\n**Winners:** {mentions}", color=discord.Color.gold())
        await channel.send(f"Congratulations {mentions}!", embed=embed)

    # =========================
    # COMMANDS
    # =========================
    @commands.hybrid_command(name="gstart", description="🎊 Start an advanced giveaway.")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(duration="10m, 1h, 1d", winners="Count", prize="Item", role_req="Required role", blacklist="Forbidden role")
    async def gstart(self, ctx, duration: str, winners: int, prize: str, role_req: discord.Role = None, blacklist: discord.Role = None):
        seconds = self.parse_time(duration)
        if not seconds: return await ctx.send("❌ Use format: 10m, 1h, 1d")

        end_ts = int(time.time()) + seconds
        embed = discord.Embed(title="🎉 Giveaway Time!", description=f"🏆 Prize: **{prize}**\n👑 Winners: **{winners}**\n⏰ Ends: <t:{end_ts}:R>", color=BRAND_COLOR)
        
        req_text = f"\n✅ Requirement: {role_req.mention}" if role_req else ""
        black_text = f"\n🚫 Blacklist: {blacklist.mention}" if blacklist else ""
        embed.add_field(name="Details", value=f"Host: {ctx.author.mention}{req_text}{black_text}")

        msg = await ctx.send(embed=embed, view=GiveawayView())
        await msg.add_reaction("🎉")

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO giveaways VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)", 
                           (msg.id, ctx.guild.id, ctx.channel.id, prize, winners, end_ts, 
                            role_req.id if role_req else None, blacklist.id if blacklist else None))
            await db.commit()

    @commands.hybrid_command(name="glist", description="📜 List all active giveaways in this server.")
    async def glist(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT prize, end_time, message_id FROM giveaways WHERE guild_id=? AND ended=0", (ctx.guild.id,)) as cur:
                active = await cur.fetchall()
        
        if not active: return await ctx.send("There are no active giveaways.")

        embed = discord.Embed(title="📜 Active Giveaways", color=BRAND_COLOR)
        for prize, end, msg_id in active:
            embed.add_field(name=prize, value=f"Ends: <t:{end}:R>\n[Jump to Message](https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{msg_id})", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    bot.add_view(GiveawayView())
    await bot.add_cog(Giveaway(bot))
