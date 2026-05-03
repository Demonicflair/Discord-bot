from discord.ext import commands
import config

class AutoMod(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @commands.Cog.listener()
    async def on_message(self,m):
        if m.author.bot: return

        if any(w in m.content.lower() for w in config.BAD_WORDS):
            await m.delete()

        if config.ANTI_LINK and "http" in m.content:
            await m.delete()

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
