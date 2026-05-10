import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

from utils.logger import get_logs, save_log, is_log_enabled

DB_PATH = "bot.db"
BOOSTER_COLOR = 0xf47fff # Discord Booster Pink

class Booster(commands.Cog):
    """
    ✨ Custom Booster Rewards
    Allows boosters to create, customize, and manage their own unique roles.
    """
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS booster_roles (
                    guild_id INTEGER,
                    user_id INTEGER,
                    role_id INTEGER,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.commit()

    # =========================
    # LOG HELPER
    # =========================
    async def send_booster_log(self, guild, text):
        logs = get_logs(guild.id)
        if logs and is_log_enabled(guild.id, "booster"):
            channel = guild.get_channel(logs[1])
            if channel:
                embed = discord.Embed(description=text, color=BOOSTER_COLOR, timestamp=discord.utils.utcnow())
                embed.set_author(name="Booster Logs", icon_url=guild.icon.url if guild.icon else None)
                await channel.send(embed=embed)
        save_log(guild.id, 0, "booster", text)

    # =========================
    # CREATE ROLE
    # =========================
    @commands.hybrid_command(name="br-create", description="Create your exclusive booster role.")
    async def br_create(self, ctx, *, name: str):
        if not ctx.author.premium_since:
            return await ctx.send("✨ This feature is reserved for **Server Boosters**!", ephemeral=True)

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT role_id FROM booster_roles WHERE guild_id=? AND user_id=?", 
                                (ctx.guild.id, ctx.author.id)) as cur:
                if await cur.fetchone():
                    return await ctx.send("❌ You already have a custom role! Use `/br-edit` to change it.", ephemeral=True)

        # Create role and move it to a safe position (below the bot's top role)
        try:
            role = await ctx.guild.create_role(name=name, color=discord.Color.random(), reason=f"Booster Role: {ctx.author}")
            
            # Smart Positioning: Try to place it below the bot's highest role to keep hierarchy clean
            await role.edit(position=ctx.guild.me.top_role.position - 1)
            await ctx.author.add_roles(role)
            
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("INSERT INTO booster_roles VALUES (?, ?, ?)", (ctx.guild.id, ctx.author.id, role.id))
                await db.commit()

            embed = discord.Embed(title="✨ Role Created", description=f"Successfully created {role.mention}!", color=role.color)
            await ctx.send(embed=embed)
            await self.send_booster_log(ctx.guild, f"✨ {ctx.author.mention} created custom role: **{name}**")
        
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create or move roles.")

    # =========================
    # EDIT ROLE (Color/Name)
    # =========================
    @commands.hybrid_command(name="br-edit", description="Update your booster role's appearance.")
    @app_commands.describe(name="New role name", color="Hex code (e.g. #ff0000)", icon_url="Image URL (Level 2+ Servers)")
    async def br_edit(self, ctx, name: str = None, color: str = None, icon_url: str = None):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT role_id FROM booster_roles WHERE guild_id=? AND user_id=?", 
                                (ctx.guild.id, ctx.author.id)) as cur:
                data = await cur.fetchone()
        
        if not data:
            return await ctx.send("❌ You don't have a booster role yet. Create one with `/br-create`.", ephemeral=True)

        role = ctx.guild.get_role(data[0])
        if not role: return await ctx.send("❌ Your role was deleted manually.")

        updates = {}
        if name: updates['name'] = name
        if color:
            try: updates['color'] = discord.Color.from_str(color)
            except: return await ctx.send("❌ Invalid Hex code.")
        
        # Elite Feature: Role Icons (Requires Server Level 2)
        if icon_url and ctx.guild.premium_tier >= 2:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(icon_url) as resp:
                        if resp.status == 200:
                            updates['display_icon'] = await resp.read()
            except: pass

        await role.edit(**updates)
        await ctx.send(f"✅ Successfully updated your role {role.mention}!", ephemeral=True)

    # =========================
    # CLEANUP LISTENERS
    # =========================
    async def cleanup_role(self, guild, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT role_id FROM booster_roles WHERE guild_id=? AND user_id=?", (guild.id, user_id)) as cur:
                data = await cur.fetchone()
            
            if data:
                role = guild.get_role(data[0])
                if role:
                    try: await role.delete(reason="User stopped boosting or left server.")
                    except: pass
                
                await db.execute("DELETE FROM booster_roles WHERE guild_id=? AND user_id=?", (guild.id, user_id))
                await db.commit()
                await self.send_booster_log(guild, f"🗑️ Deleted custom role for user ID: `{user_id}`")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # If they used to boost and now they don't
        if before.premium_since and not after.premium_since:
            await self.cleanup_role(after.guild, after.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # If a booster leaves the server, delete their role to save role slots
        await self.cleanup_role(member.guild, member.id)

async def setup(bot):
    await bot.add_cog(Booster(bot))
