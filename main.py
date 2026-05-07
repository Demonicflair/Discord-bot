import discord
from discord.ext import commands
import asyncio
import config
import os
import time
import traceback

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

# =========================
# BOT SETUP
# =========================
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    case_insensitive=True
)

startup_time = time.time()

# =========================
# LOAD COGS
# =========================
async def load_cogs():
    loaded = 0
    failed = 0

    print("━━━━━━━━━━━━━━━━━━━━━━")
    print("Loading Cogs...")
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
    print(f"🤖 Logged in as {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Servers: {len(bot.guilds)}")
    print("━━━━━━━━━━━━━━━━━━━━━━")

    # =========================
    # SYNC COMMANDS
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

    uptime = round(time.time() - startup_time, 2)

    print(f"🚀 Startup Time: {uptime}s")
    print("━━━━━━━━━━━━━━━━━━━━━━")


# =========================
# COMMAND ERROR HANDLER
# =========================
@bot.event
async def on_command_error(ctx, error):

    if hasattr(ctx.command, "on_error"):
        return

    error = getattr(error, "original", error)

    # =========================
    # MISSING PERMS
    # =========================
    if isinstance(error, commands.MissingPermissions):

        perms = ", ".join(error.missing_permissions)

        embed = discord.Embed(
            description=f"❌ Missing permissions:\n`{perms}`",
            color=discord.Color.red()
        )

        return await ctx.send(embed=embed)

    # =========================
    # BOT MISSING PERMS
    # =========================
    elif isinstance(error, commands.BotMissingPermissions):

        perms = ", ".join(error.missing_permissions)

        embed = discord.Embed(
            description=f"❌ I need permissions:\n`{perms}`",
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
                f"`{ctx.prefix}{ctx.command} {ctx.command.signature}`"
            ),
            color=discord.Color.orange()
        )

        return await ctx.send(embed=embed)

    # =========================
    # BAD ARGUMENT
    # =========================
    elif isinstance(error, commands.BadArgument):

        embed = discord.Embed(
            description="❌ Invalid argument provided.",
            color=discord.Color.red()
        )

        return await ctx.send(embed=embed)

    # =========================
    # COOLDOWN
    # =========================
    elif isinstance(error, commands.CommandOnCooldown):

        embed = discord.Embed(
            description=f"⏳ Try again in `{round(error.retry_after, 1)}s`",
            color=discord.Color.orange()
        )

        return await ctx.send(embed=embed)

    # =========================
    # COMMAND NOT FOUND
    # =========================
    elif isinstance(error, commands.CommandNotFound):
        return

    # =========================
    # UNKNOWN ERROR
    # =========================
    else:

        embed = discord.Embed(
            title="❌ Unexpected Error",
            description="An internal error occurred.",
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)

        print("━━━━━━━━━━━━━━━━━━━━━━")
        print("❌ COMMAND ERROR")
        print("━━━━━━━━━━━━━━━━━━━━━━")

        traceback.print_exception(type(error), error, error.__traceback__)


# =========================
# BOT STARTUP
# =========================
async def main():

    async with bot:

        await load_cogs()

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
