from discord.ext import commands
import time, database, config

class AntiNuke(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
        self.actions={}

    def track(self,u):
        now=time.time()
        self.actions.setdefault(u,[]).append(now)
        self.actions[u]=[t for t in self.actions[u] if now-t<10]
        return len(self.actions[u])

    @commands.Cog.listener()
    async def on_member_ban(self,guild,user):
        if database.is_whitelisted(user.id,guild.id): return

        if self.track(user.id)>=config.ANTI_NUKE_LIMIT:
            m=guild.get_member(user.id)
            if m:
                await m.edit(roles=[])

async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
