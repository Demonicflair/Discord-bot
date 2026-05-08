import discord
from discord.ext import commands
import asyncio
import config
import os
import time
import traceback
import sqlite3

# =========================
# DATABASE
# =========================
prefix_db = sqlite3.connect(
    "prefixes.db",
    check_same_thread=False
)

prefix_cursor = prefix_db.cursor()

prefix_cursor.execute("""
CREATE TABLE IF NOT EXISTS prefixes(
    guild_id INTEGER PRIMARY KEY,
    prefix TEXT
)
""")

prefix_db.commit()

DEFAULT_PREFIX = "!"

# =========================
# DYNAMIC PREFIX
# =========================
def get_prefix(bot, message):

    if not message.guild:
        return DEFAULT_PREFIX

    prefix_cursor.execute(
        "SELECT prefix FROM prefixes WHERE guild_id=?",
        (message.guild.id,)
    )

    data = prefix_cursor.fetchone()

    if data:
        return data[0]

    return DEFAULT_PREFIX

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True
intents.presences = True
intents.voice_states = True
intents.emojis_and_stickers = True

# =========================
# BOT SETUP
# =========================
bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True,
    strip_after_prefix=True
)

startup_time = time.time()

# =========================
# STATUS ROTATION
# =========================
async def status_task():

    await bot.wait_until_ready()

    statuses = [
        "🛡️ Protecting servers",
        "⚡ Ultimate Moderation",
        "🎫 Advanced Ticket System",
        "💣 Anti-Nuke Enabled",
        "🔨 Moderating Members",
        "📚 /help",
        "🚀 Elite Discord Bot"
    ]

    index = 0

    while not bot.is_closed():

        try:
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=statuses[index]
                ),
                status=discord.Status.online
            )

            index = (index + 1) % len(statuses)

            await asyncio.sleep(20)

        except:
            pass

# =========================
# LOAD COGS
# =========================
async def load_cogs():

    loaded = 0
    failed = 0

    print("━━━━━━━━━━━━━━━━━━━━━━")
    print("🚀 Loading Cogs...")
    print("━━━━━━━━━━━━━━━━━━━━━━")

    for filename in os.listdir("./cogs"):

        if not filename.endswith(".py"):
            continue

        cog = f"cogs.{filename[:-3]}"

        try:

            await bot.load_extension(cog)

            print(f"✅ Loaded: {filename}")

            loaded += 1

        except Exception as e:

            failed += 1

            print(f"❌ Failed: {filename}")
            print(f"{type(e).__name__}: {e}")

    print("━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Loaded: {loaded}")
    print(f"❌ Failed: {failed}")
    print("━━━━━━━━━━━━━━━━━━━━━━")

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():

    print("━━━━━━━━━━━━━━━━━━━━━━")
    print("🤖 BOT ONLINE")
    print("━━━━━━━━━━━━━━━━━━━━━━")

    print(f"👤 Username : {bot.user}")
    print(f"🆔 Bot ID   : {bot.user.id}")
    print(f"🌐 Servers  : {len(bot.guilds)}")
    print(f"👥 Users    : {len(bot.users)}")

    print("━━━━━━━━━━━━━━━━━━━━━━")

    # =========================
    # SYNC SLASH COMMANDS
    # =========================
    try:

        synced = await bot.tree.sync()

        print(f"✅ Synced {len(synced)} slash commands")

    except Exception as e:

        print("❌ Slash Sync Error")
        print(e)

    # =========================
    # LATENCY
    # =========================
    latency = round(bot.latency * 1000)

    print(f"⚡ Ping: {latency}ms")

    # =========================
    # UPTIME
    # =========================
    uptime = round(time.time() - startup_time, 2)

    print(f"🚀 Startup Time: {uptime}s")

    print("━━━━━━━━━━━━━━━━━━━━━━")

# =========================
# GUILD JOIN
# =========================
@bot.event
async def on_guild_join(guild):

    print(f"📥 Joined Guild: {guild.name}")

    try:

        owner = guild.owner

        if owner:

            embed = discord.Embed(
                title="🤖 Thanks for inviting me!",
                description=(
                    "Use `/help` or `!help`\n\n"
                    "⚡ Features:\n"
                    "• Moderation\n"
                    "• Anti-Nuke\n"
                    "• Security\n"
                    "• Tickets\n"
                    "• Giveaways\n"
                    "• Welcome System\n"
                    "• Utility Commands\n"
                    "• AFK System\n"
                    "• Booster Roles\n"
                    "• Logging System"
                ),
                color=discord.Color.blurple()
            )

            embed.set_footer(
                text="Elite Discord System"
            )

            await owner.send(embed=embed)

    except:
        pass

# =========================
# COMMAND LOGGER
# =========================
@bot.event
async def on_command(ctx):

    print(
        f"⚡ {ctx.author} used "
        f"{ctx.command} in "
        f"{ctx.guild.name}"
    )

# =========================
# ERROR HANDLER
# =========================
@bot.event
async def on_command_error(ctx, error):

    if hasattr(ctx.command, "on_error"):
        return

    error = getattr(error, "original", error)

    # =========================
    # MISSING PERMISSIONS
    # =========================
    if isinstance(error, commands.MissingPermissions):

        perms = ", ".join(error.missing_permissions)

        embed = discord.Embed(
            title="❌ Missing Permissions",
            description=f"You need:\n`{perms}`",
            color=discord.Color.red()
        )

        return await ctx.send(embed=embed)

    # =========================
    # BOT MISSING PERMISSIONS
    # =========================
    elif isinstance(error, commands.BotMissingPermissions):

        perms = ", ".join(error.missing_permissions)

        embed = discord.Embed(
            title="❌ Missing Bot Permissions",
            description=f"I need:\n`{perms}`",
            color=discord.Color.red()
        )

        return await ctx.send(embed=embed)

    # =========================
    # MISSING ARGUMENT
    # =========================
    elif isinstance(error, commands.MissingRequiredArgument):

        embed = discord.Embed(
            title="❌ Missing Argument",
            description=(
                f"Usage:\n"
                f"`{ctx.prefix}{ctx.command} "
                f"{ctx.command.signature}`"
            ),
            color=discord.Color.orange()
        )

        return await ctx.send(embed=embed)

    # =========================
    # BAD ARGUMENT
    # =========================
    elif isinstance(error, commands.BadArgument):

        embed = discord.Embed(
            title="❌ Invalid Argument",
            description="Invalid argument provided.",
            color=discord.Color.red()
        )

        return await ctx.send(embed=embed)

    # =========================
    # COMMAND COOLDOWN
    # =========================
    elif isinstance(error, commands.CommandOnCooldown):

        embed = discord.Embed(
            title="⏳ Slow Down",
            description=(
                f"Try again in "
                f"`{round(error.retry_after, 1)}s`"
            ),
            color=discord.Color.orange()
        )

        return await ctx.send(embed=embed)

    # =========================
    # COMMAND NOT FOUND
    # =========================
    elif isinstance(error, commands.CommandNotFound):

        return

    # =========================
    # NO PRIVATE MESSAGE
    # =========================
    elif isinstance(error, commands.NoPrivateMessage):

        embed = discord.Embed(
            description="❌ Cannot use this command in DMs.",
            color=discord.Color.red()
        )

        return await ctx.send(embed=embed)

    # =========================
    # UNKNOWN ERROR
    # =========================
    else:

        embed = discord.Embed(
            title="❌ Unexpected Error",
            description=(
                "An internal error occurred.\n"
                "Check console for details."
            ),
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)

        print("━━━━━━━━━━━━━━━━━━━━━━")
        print("❌ COMMAND ERROR")
        print("━━━━━━━━━━━━━━━━━━━━━━")

        traceback.print_exception(
            type(error),
            error,
            error.__traceback__
        )

# =========================
# BOT STARTUP
# =========================
async def main():

    async with bot:

        await load_cogs()

        bot.loop.create_task(status_task())

        try:

            await bot.start(config.TOKEN)

        except KeyboardInterrupt:

            print("🛑 Bot shutting down")

        except Exception as e:

            print("❌ Fatal Startup Error")
            print(e)

# =========================
# RUN BOT
# =========================
asyncio.run(main())
