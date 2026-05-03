import config

async def log(guild, msg):
    for ch in guild.text_channels:
        if ch.name == config.LOG_CHANNEL:
            await ch.send(msg)