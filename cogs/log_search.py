import discord
from discord.ext import commands
from discord import app_commands
from utils.logger import search_logs_db

class LogSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="searchlogs")
    @app_commands.describe(query="Search logs", log_type="Filter type")
    async def searchlogs(self, ctx, query: str, log_type: str = None):

        results = search_logs_db(ctx.guild.id, query, log_type)

        if not results:
            return await ctx.send("❌ No logs found")

        desc = ""
        for r in results:
            desc += f"📝 {r[3]}\n🕒 {r[4]}\n\n"

        embed = discord.Embed(
            title=f"🔎 Logs: {query}",
            description=desc[:4000],
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LogSearch(bot))
