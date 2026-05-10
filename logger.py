import discord
import config
from utils.logger import get_logs, is_log_enabled

async def log(guild, log_type, message=None, embed=None):
    """
    Elite Log Dispatcher:
    - Automatically finds the right channel (Mod vs Bot).
    - Checks if the specific log type is enabled.
    - Supports both plain text and professional embeds.
    """
    
    # 1. Get the saved channel IDs from the database
    channels = await get_logs(guild.id)
    if not channels:
        return # Logging not setup for this server

    mod_ch_id, bot_ch_id = channels

    # 2. Check if this specific log (e.g., 'ban') is enabled
    if not await is_log_enabled(guild.id, log_type):
        return

    # 3. Decide which channel to send to
    # Moderation types go to Mod-Log, everything else to Bot-Log
    mod_types = ["ban", "unban", "kick", "warn", "mute", "unmute"]
    target_id = mod_ch_id if log_type in mod_types else bot_ch_id
    
    channel = guild.get_channel(target_id)
    if not channel:
        return # Channel was deleted or bot lacks view perms

    # 4. Dispatch the message
    try:
        if embed:
            await channel.send(content=message, embed=embed)
        else:
            await channel.send(content=message)
    except discord.Forbidden:
        print(f"[!] Missing Permissions to log in {guild.name}")
        
