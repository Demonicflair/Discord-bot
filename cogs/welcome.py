import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import datetime

DB_PATH = "bot.db"
BRAND_COLOR = 0x2b2d31

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS welcome_settings (
                    guild_id INTEGER PRIMARY KEY,
                    welcome_channel INTEGER,
                    leave_channel INTEGER,
                    welcome_message TEXT DEFAULT 'Welcome {user} to {server}!',
                    leave_message TEXT DEFAULT '{user} has left {server}.',
                    autorole INTEGER,
                    use_embed INTEGER DEFAULT 1,
                    embed_color TEXT DEFAULT '2b2d31',
                    show_thumbnail INTEGER DEFAULT 1
                )
            """)
            await db.commit()

    # =========================
    # THE DEM VARIABLE ENGINE
    # =========================
    def format_msg(self, text, member: discord.Member):
        vars = {
            "{user}": member.mention,
            "{user_name}": member.name,
            "{user_id}": str(member.id),
            "{server}": member.guild.name,
            "{member_count}": str(member.guild.member_count),
            "{count_suffix}": "th" if str(member.guild.member_count).endswith(("11", "12", "13")) else {1: "st", 2: "nd", 3: "rd"}.get(member.guild.member_count % 10, "th"),
            "{created_at}": f"<t:{int(member.created_at.timestamp())}:R>",
            "{owner}": member.guild.owner.mention
        }
        for key, value in vars.items():
            text = text.replace(key, value)
        return text

    # =========================
    # INTERNAL SENDERS (For Events & Tests)
    # =========================
    async def send_welcome(self, member):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM welcome_settings WHERE guild_id=?", (member.guild.id,)) as cur:
                data = await cur.fetchone()
        
        if not data or not data[1]: return
        w_chan, w_msg, use_embed, color, thumb = data[1], data[3], data[6], data[7], data[8]
        
        channel = member.guild.get_channel(w_chan)
        if channel:
            desc = self.format_msg(w_msg, member)
            if use_embed:
                embed = discord.Embed(description=desc, color=int(color, 16), timestamp=discord.utils.utcnow())
                if thumb: embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_author(name=f"Welcome to {member.guild.name}", icon_url=member.guild.icon.url if member.guild.icon else None)
                await channel.send(content=member.mention, embed=embed)
            else:
                await channel.send(desc)

    async def send_leave(self, member):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM welcome_settings WHERE guild_id=?", (member.guild.id,)) as cur:
                data = await cur.fetchone()
        
        if not data or not data[2]: return
        l_chan, l_msg, color = data[2], data[4], data[7]
        
        channel = member.guild.get_channel(l_chan)
        if channel:
            desc = self.format_msg(l_msg, member)
            embed = discord.Embed(description=desc, color=int(color, 16))
            embed.set_footer(text="Member Left Dem System")
            await channel.send(embed=embed)

    # =========================
    # LISTENERS
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.send_welcome(member)
        # Autorole Logic
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT autorole FROM welcome_settings WHERE guild_id=?", (member.guild.id,)) as cur:
                res = await cur.fetchone()
                if res and res[0]:
                    role = member.guild.get_role(res[0])
                    if role: await member.add_roles(role)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.send_leave(member)

    # =========================
    # HYBRID COMMANDS
    # =========================
    @commands.hybrid_group(name="welcome", description="Dem Welcome System configuration.")
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @welcome.command(name="test_greet", description="🧪 Test the Welcome (Greet) message.")
    async def test_greet(self, ctx):
        await self.send_welcome(ctx.author)
        await ctx.send("✅ Sent a test **Welcome** message.", ephemeral=True)

    @welcome.command(name="test_leave", description="🧪 Test the Leave message.")
    async def test_leave(self, ctx):
        await self.send_leave(ctx.author)
        await ctx.send("✅ Sent a test **Leave** message.", ephemeral=True)

    @welcome.command(name="variables", description="📖 View all available placeholders for Dem.")
    async def variables(self, ctx):
        embed = discord.Embed(title="📖 Dem Variable Guide", color=BRAND_COLOR)
        embed.description = (
            "`{user}` - Mentions the user\n"
            "`{user_name}` - Plain username\n"
            "`{server}` - Server Name\n"
            "`{member_count}` - Total members\n"
            "`{count_suffix}` - st, nd, rd, th\n"
            "`{created_at}` - Account age\n"
            "`{owner}` - Mentions the owner"
        )
        await ctx.send(embed=embed)

    @welcome.command(name="reset", description="♻️ Reset all Dem welcome settings for this server.")
    async def reset_welcome(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM welcome_settings WHERE guild_id=?", (ctx.guild.id,))
            await db.commit()
        await ctx.send("♻️ **Dem Welcome Settings** have been reset to factory defaults.")

    @welcome.command(name="setup", description="🚀 Set Join/Leave channels.")
    async def setup(self, ctx, welcome: discord.TextChannel = None, leave: discord.TextChannel = None):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO welcome_settings (guild_id, welcome_channel, leave_channel) 
                VALUES (?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET 
                welcome_channel=COALESCE(?, welcome_channel), 
                leave_channel=COALESCE(?, leave_channel)
            """, (ctx.guild.id, getattr(welcome, 'id', None), getattr(leave, 'id', None), 
                  getattr(welcome, 'id', None), getattr(leave, 'id', None)))
            await db.commit()
        await ctx.send("✅ Dem Channels updated.")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
    
