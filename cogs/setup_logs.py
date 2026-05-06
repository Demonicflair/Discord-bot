import discord
from discord.ext import commands
from utils.logger import cursor, db

class SetupLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.create_logs(guild)

    async def create_logs(self, guild):
        existing = cursor.execute(
            "SELECT * FROM log_channels WHERE guild_id=?",
            (guild.id,)
        ).fetchone()

        if existing:
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)

        mod_log = await guild.create_text_channel("mod-logs", overwrites=overwrites)
        bot_log = await guild.create_text_channel("bot-logs", overwrites=overwrites)

        cursor.execute(
            "INSERT INTO log_channels VALUES (?, ?, ?)",
            (guild.id, mod_log.id, bot_log.id)
        )
        db.commit()

        await mod_log.send("📄 Moderation logs here")
        await bot_log.send("🤖 Bot logs here")

async def setup(bot):
    await bot.add_cog(SetupLogs(bot))
