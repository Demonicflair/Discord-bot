from discord.ext import commands
import discord
import config
import logger

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ MEMBER JOIN
    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild

        # Auto role
        role = discord.utils.get(guild.roles, name=config.AUTO_ROLE) if hasattr(config, "AUTO_ROLE") else None
        if role:
            await member.add_roles(role)

        # Send welcome message
        await logger.log(guild, f"✅ {member} joined the server")

    # ❌ MEMBER LEAVE
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        await logger.log(guild, f"❌ {member} left the server")

    # 🗑️ MESSAGE DELETE LOG
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        await logger.log(
            message.guild,
            f"🗑️ Message deleted in #{message.channel}: {message.author} → {message.content}"
        )

    # ✏️ MESSAGE EDIT LOG
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return

        if before.content != after.content:
            await logger.log(
                before.guild,
                f"✏️ Edited in #{before.channel}: {before.author}\nBefore: {before.content}\nAfter: {after.content}"
            )

async def setup(bot):
    await bot.add_cog(Events(bot))
