import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio

DB_PATH = "data.db"

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # 🧠 VARIABLE ENGINE
    # =========================
    def format_msg(self, text, member: discord.Member):
        """Replaces placeholders with actual server data."""
        # Handling the ordinal suffix for member count (1st, 2nd, 3rd, etc.)
        count = member.guild.member_count
        suffix = "th" if 11 <= count % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(count % 10, "th")
        
        placeholders = {
            "{user}": member.mention,
            "{user_name}": member.name,
            "{server}": member.guild.name,
            "{member_count}": str(count),
            "{count_suffix}": suffix,
            "{owner}": member.guild.owner.mention
        }
        for key, value in placeholders.items():
            text = text.replace(key, value)
        return text

    # =========================
    # 📥 ON MEMBER JOIN
    # =========================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT * FROM welcome_settings WHERE guild_id=?", (member.guild.id,)) as cur:
                data = await cur.fetchone()
        
        if not data: return
        
        # Unpacking: w_chan, l_chan, w_msg, l_msg, role_id, use_embed
        _, w_chan, _, w_msg, _, role_id, use_embed = data

        # 1. SEND WELCOME MESSAGE
        channel = member.guild.get_channel(w_chan)
        if channel:
            content = self.format_msg(w_msg or "Welcome {user} to {server}!", member)
            if use_embed:
                embed = discord.Embed(description=content, color=0x2b2d31)
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_author(name=f"New Member Joined!", icon_url=member.guild.icon.url if member.guild.icon else None)
                await channel.send(embed=embed)
            else:
                await channel.send(content)

        # 2. AUTO-ROLE (With "Big Bot" 2s Delay for Stability)
        if role_id:
            await asyncio.sleep(2)
            role = member.guild.get_role(role_id)
            if role:
                try: await member.add_roles(role, reason="Dem Auto-Role")
                except: pass

    # =========================
    # ⚙️ HYBRID CONFIGURATION
    # =========================
    @commands.hybrid_group(name="welcome", description="🏠 Configure join/leave messages.")
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `!welcome setup` or `!welcome msg` to configure.")

    @welcome.command(name="setup", description="🚀 Set the welcome channel and auto-role.")
    @app_commands.describe(channel="Where to send messages", role="Role to give on join")
    async def setup_welcome(self, ctx, channel: discord.TextChannel, role: discord.Role = None):
        role_id = role.id if role else None
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO welcome_settings (guild_id, welcome_channel, autorole, use_embed) 
                VALUES (?, ?, ?, 1) ON CONFLICT(guild_id) 
                DO UPDATE SET welcome_channel=excluded.welcome_channel, autorole=excluded.autorole
            """, (ctx.guild.id, channel.id, role_id))
            await db.commit()
        await ctx.send(f"✅ Welcome system set to {channel.mention}. Auto-role: {role.mention if role else 'None'}")

    @welcome.command(name="msg", description="📝 Set a custom welcome message.")
    @app_commands.describe(text="The message (Use {user}, {server}, etc.)")
    async def set_msg(self, ctx, *, text: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE welcome_settings SET welcome_message=? WHERE guild_id=?", (text, ctx.guild.id))
            await db.commit()
        await ctx.send(f"✅ Welcome message updated!\n**Preview:** {self.format_msg(text, ctx.author)}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
