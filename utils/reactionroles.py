import discord
import aiosqlite

from discord.ext import commands
from discord import app_commands

from utils.embeds import success_embed, error_embed, neutral_embed
from utils.dispatch import dispatch_log
from utils.config import DB_PATH


# =========================
# DATABASE SETUP
# =========================

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS reaction_roles (
    guild_id INTEGER,
    channel_id INTEGER,
    message_id INTEGER,
    role_id INTEGER,
    emoji TEXT
)
"""


# =========================
# REACTION ROLE VIEW
# =========================

class ReactionRoleView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Select your roles...",
        min_values=1,
        max_values=1,
        custom_id="dem_reactionroles"
    )
    async def role_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select
    ):

        guild = interaction.guild
        member = interaction.user

        selected = select.values[0]

        role_id = int(selected)

        role = guild.get_role(role_id)

        if not role:

            return await interaction.response.send_message(
                embed=error_embed(
                    "Role no longer exists."
                ),
                ephemeral=True
            )

        # =========================
        # TOGGLE ROLE
        # =========================

        if role in member.roles:

            await member.remove_roles(
                role,
                reason="Reaction Role Remove"
            )

            await interaction.response.send_message(
                embed=neutral_embed(
                    f"Removed {role.mention}"
                ),
                ephemeral=True
            )

        else:

            await member.add_roles(
                role,
                reason="Reaction Role Add"
            )

            await interaction.response.send_message(
                embed=success_embed(
                    f"Added {role.mention}"
                ),
                ephemeral=True
            )


# =========================
# REACTION ROLE COG
# =========================

class ReactionRoles(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================
    # LOAD DATABASE
    # =========================

    async def cog_load(self):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute(CREATE_TABLES)

            await db.commit()

    # =========================
    # GROUP
    # =========================

    @commands.hybrid_group(
        name="reactionrole",
        description="Reaction role system."
    )
    @commands.has_permissions(
        manage_roles=True
    )
    async def reactionrole(self, ctx):

        if ctx.invoked_subcommand is None:

            embed = neutral_embed(
                "Reaction Role Commands"
            )

            embed.add_field(
                name="Commands",
                value=(
                    "`reactionrole create`\n"
                    "`reactionrole delete`\n"
                    "`reactionrole list`"
                ),
                inline=False
            )

            await ctx.send(embed=embed)

    # =========================
    # CREATE PANEL
    # =========================

    @reactionrole.command(
        name="create",
        description="Create a reaction role panel."
    )
    @app_commands.describe(
        title="Panel title",
        description="Panel description"
    )
    async def create_panel(
        self,
        ctx,
        title: str,
        description: str
    ):

        embed = discord.Embed(
            title=title,
            description=description,
            color=0x2b2d31
        )

        view = ReactionRoleView()

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
                SELECT role_id, emoji
                FROM reaction_roles
                WHERE guild_id = ?
            """, (
                ctx.guild.id,
            )) as cursor:

                data = await cursor.fetchall()

        if not data:

            return await ctx.send(
                embed=error_embed(
                    "No reaction roles configured.\nUse `/reactionrole add` first."
                )
            )

        select = view.children[0]

        for role_id, emoji in data:

            role = ctx.guild.get_role(role_id)

            if not role:
                continue

            select.add_option(
                label=role.name,
                value=str(role.id),
                emoji=emoji
            )

        msg = await ctx.send(
            embed=embed,
            view=view
        )

        await dispatch_log(
            guild=ctx.guild,
            log_type="reactionroles",
            content=(
                f"🎭 Reaction Role Panel Created\n"
                f"Moderator: {ctx.author}\n"
                f"Message ID: {msg.id}"
            ),
            moderator_id=ctx.author.id
        )

    # =========================
    # ADD ROLE
    # =========================

    @reactionrole.command(
        name="add",
        description="Add a role option."
    )
    @app_commands.describe(
        role="Role to give",
        emoji="Emoji for role"
    )
    async def add_role(
        self,
        ctx,
        role: discord.Role,
        emoji: str
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                INSERT INTO reaction_roles
                (
                    guild_id,
                    channel_id,
                    message_id,
                    role_id,
                    emoji
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                ctx.guild.id,
                0,
                0,
                role.id,
                emoji
            ))

            await db.commit()

        await ctx.send(
            embed=success_embed(
                f"Added {role.mention} with emoji {emoji}"
            )
        )

    # =========================
    # REMOVE ROLE
    # =========================

    @reactionrole.command(
        name="delete",
        description="Delete a reaction role."
    )
    async def delete_role(
        self,
        ctx,
        role: discord.Role
    ):

        async with aiosqlite.connect(DB_PATH) as db:

            await db.execute("""
                DELETE FROM reaction_roles
                WHERE guild_id = ?
                AND role_id = ?
            """, (
                ctx.guild.id,
                role.id
            ))

            await db.commit()

        await ctx.send(
            embed=success_embed(
                f"Removed {role.mention} from reaction roles."
            )
        )

    # =========================
    # LIST
    # =========================

    @reactionrole.command(
        name="list",
        description="View reaction roles."
    )
    async def list_roles(self, ctx):

        async with aiosqlite.connect(DB_PATH) as db:

            async with db.execute("""
                SELECT role_id, emoji
                FROM reaction_roles
                WHERE guild_id = ?
            """, (
                ctx.guild.id,
            )) as cursor:

                data = await cursor.fetchall()

        if not data:

            return await ctx.send(
                embed=error_embed(
                    "No reaction roles setup."
                )
            )

        embed = discord.Embed(
            title="🎭 Reaction Roles",
            color=0x2b2d31
        )

        for role_id, emoji in data:

            role = ctx.guild.get_role(role_id)

            if not role:
                continue

            embed.add_field(
                name=role.name,
                value=f"Emoji: {emoji}",
                inline=False
            )

        await ctx.send(embed=embed)


# =========================
# LOAD
# =========================

async def setup(bot):

    await bot.add_cog(
        ReactionRoles(bot)
      )
