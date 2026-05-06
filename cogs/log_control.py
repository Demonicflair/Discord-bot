from discord.ext import commands
from utils.logger import set_log

class LogControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def log_enable(self, ctx, log: str):
        set_log(ctx.guild.id, log, True)
        await ctx.send(f"✅ Enabled {log} logs")

    @commands.hybrid_command()
    async def log_disable(self, ctx, log: str):
        set_log(ctx.guild.id, log, False)
        await ctx.send(f"❌ Disabled {log} logs")

async def setup(bot):
    await bot.add_cog(LogControl(bot))
