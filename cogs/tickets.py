import discord
from discord.ext import commands
from discord.ui import View

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green)
    async def open(self, i, b):
        ch = await i.guild.create_text_channel(f"ticket-{i.user.name}")
        await ch.send(f"{i.user.mention} support will assist you")
        await i.response.send_message("Created", ephemeral=True)

class Tickets(commands.Cog):
    def __init__(self,bot): self.bot=bot

    @commands.command()
    async def panel(self, ctx):
        await ctx.send("Open ticket:", view=TicketView())

async def setup(bot):
    await bot.add_cog(Tickets(bot))
