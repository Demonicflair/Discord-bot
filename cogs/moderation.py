from discord.ext import commands
import discord, database, logger

class Moderation(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @commands.command()
    async def warn(self, ctx, member: discord.Member):
        c = database.add_warn(member.id, ctx.guild.id)
        await ctx.send(f"{member} warned ({c})")

        if c >= 3:
            await member.timeout(discord.utils.utcnow())

        await logger.log(ctx.guild, f"{member} warned")

    @commands.command()
    async def whitelist(self, ctx, member: discord.Member):
        database.add_whitelist(member.id, ctx.guild.id)
        await ctx.send("Whitelisted")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
