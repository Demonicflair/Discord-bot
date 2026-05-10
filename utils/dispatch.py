import discord
from utils.logger import get_logs, is_log_enabled

async def log(guild, log_type, message=None, embed=None):
    """
    Elite Log Dispatcher:
    - Finds the correct channel (Mod vs Bot).
    - Checks if the user enabled this specific log type.
    - Handles text and embeds instantly.
    """
    
    # 1. Fetch channel IDs from Database
    channels = await get_logs(guild.id)
    if not channels:
        return # Logging system not set up for this guild

    mod_ch_id, bot_ch_id = channels

    # 2. Check if the specific log type is enabled (via /log_enable)
    if not await is_log_enabled(guild.id, log_type):
        return

    # 3. Determine target channel
    # Moderation actions go to mod-logs, everything else (security, tickets, etc.) goes to bot-logs
    mod_actions = ["ban", "unban", "kick", "warn", "mute", "unmute"]
    target_id = mod_ch_id if log_type in mod_actions else bot_ch_id
    
    channel = guild.get_channel(target_id)
    if not channel:
        return # Channel was deleted or bot lacks view permissions

    # 4. Send the log
    try:
        if embed:
            await channel.send(content=message, embed=embed)
        else:
            await channel.send(content=message)
    except discord.Forbidden:
        print(f"[!] Warning: Missing permissions to send logs in {guild.name}")
    except Exception as e:
        print(f"[!] Log Error in {guild.name}: {e}")
      
