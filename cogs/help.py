import discord

from discord.ext import commands
from utils.config import BRAND_COLOR


HELP_DATA = {

    "Security System": {
        "emoji": "🛡️",
        "title": "Security & Protection",
        "description":
            "Protect your server using intelligent security systems.",
        "fields": [

            (
                "Main Commands",

                "`/security status`\n"
                "`/security reset`\n"
                "`/log_enable`\n"
                "`/log_disable`"
            ),

            (
                "Features",

                "• Scam detection\n"
                "• Mass mention protection\n"
                "• Heat system\n"
                "• Auto punishments\n"
                "• Security logs"
            )
        ]
    },

    "Moderation": {

        "emoji": "🔨",

        "title": "Moderation Commands",

        "description":
            "Powerful moderation tools for staff teams.",

        "fields": [

            (
                "Punishments",

                "`/ban`\n"
                "`/kick`\n"
                "`/warn`\n"
                "`/clear`"
            ),

            (
                "Investigation",

                "`/history`\n"
                "`/mod_stats`"
            )
        ]
    },

    "Tickets & Support": {

        "emoji": "🎫",

        "title": "Ticket System",

        "description":
            "Advanced support ticket management.",

        "fields": [

            (
                "Commands",

                "`/ticket setup`\n"
                "`/ticket blacklist`\n"
                "`/ticket stats`"
            ),

            (
                "Features",

                "• Persistent buttons\n"
                "• Ticket transcripts\n"
                "• Claim system\n"
                "• Staff workflow"
            )
        ]
    },

    "Utility": {

        "emoji": "⚙️",

        "title": "Utility",

        "description":
            "Everyday utility commands.",

        "fields": [

            (
                "Commands",

                "`/afk`\n"
                "`/help`\n"
                "`/setuplogs`\n"
                "`/log_settings`"
            )
        ]
    },

    "Welcome & Automation": {

        "emoji": "👋",

        "title": "Welcome System",

        "description":
            "Automatic welcomes and onboarding.",

        "fields": [

            (
                "Commands",

                "`/welcome setup`\n"
                "`/welcome message`\n"
                "`/welcome embeds`"
            ),

            (
                "Features",

                "• Autoroles\n"
                "• Placeholders\n"
                "• Join/Leave messages"
            )
        ]
    },

    "Giveaways": {

        "emoji": "🎉",

        "title": "Giveaways",

        "description":
            "Advanced giveaway system.",

        "fields": [

            (
                "Commands",

                "`/gstart`\n"
                "`/glist`"
            ),

            (
                "Features",

                "• Requirements\n"
                "• Blacklists\n"
                "• Persistent buttons\n"
                "• Auto winners"
            )
        ]
    }
}


class HelpDropdown(discord.ui.Select):

    def __init__(self, bot, owner_id):

        self.bot = bot
        self.owner_id = owner_id

        options = [

            discord.SelectOption(

                label=name,

                emoji=data["emoji"],

                description=data["description"][:100]

            )

            for name, data in HELP_DATA.items()

        ]

        super().__init__(

            placeholder="Select category...",

            options=options,

            min_values=1,

            max_values=1

        )

    async def callback(

        self,

        interaction: discord.Interaction

    ):

        if interaction.user.id != self.owner_id:

            return await interaction.response.send_message(

                "This help menu belongs to someone else.",

                ephemeral=True

            )

        selected = HELP_DATA[self.values[0]]

        embed = discord.Embed(

            title=f"{selected['emoji']} {selected['title']}",

            description=selected["description"],

            color=BRAND_COLOR

        )

        for name, value in selected["fields"]:

            embed.add_field(

                name=name,

                value=value,

                inline=False

            )

        if self.bot.user:

            embed.set_thumbnail(

                url=self.bot.user.display_avatar.url

            )

        embed.set_footer(

            text="Dem Security"

        )

        await interaction.response.edit_message(

            embed=embed,

            view=self.view

        )


class HelpView(discord.ui.View):

    def __init__(

        self,

        bot,

        owner_id

    ):

        super().__init__(timeout=180)

        self.add_item(

            HelpDropdown(

                bot,

                owner_id

            )

        )

    async def on_timeout(self):

        for item in self.children:

            item.disabled = True


class Help(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @commands.hybrid_command(

        name="help",

        description="Open help menu."

    )
    async def help(

        self,

        ctx

    ):

        embed = discord.Embed(

            title="Dem Security",

            description=(

                "Advanced moderation and protection bot.\n\n"

                "Select a category below."

            ),

            color=BRAND_COLOR

        )

        embed.add_field(

            name="Main Features",

            value=(

                "• Security\n"

                "• Moderation\n"

                "• Tickets\n"

                "• Welcome\n"

                "• Giveaways\n"

                "• Logging"

            ),

            inline=False

        )

        if self.bot.user:

            embed.set_thumbnail(

                url=self.bot.user.display_avatar.url

            )

        embed.set_footer(

            text="Slash Commands Enabled"

        )

        await ctx.send(

            embed=embed,

            view=HelpView(

                self.bot,

                ctx.author.id

            )

        )


async def setup(bot):

    await bot.add_cog(

        Help(bot)

    )
