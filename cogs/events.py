import discord
from discord.ext import commands
from utils.dispatch import dispatch_log # Centralized logging system

class Events(commands.Cog):
    """
    📡 The Event Watcher
    Handles automated logging for message edits, deletions, and member updates.
    """
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # 📝 MESSAGE LOGGING
    # =========================
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild: return
        
        content = message.content if message.content else "*No text content (Image or Embed)*"
        await dispatch_log(
            message.guild, 
            "message_delete", 
            f"🗑️ **Message Deleted in {message.channel.mention}**\n"
            f"**Author:** {message.author}\n"
            f"**Content:** {content}"
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content: return
        
        await dispatch_log(
            before.guild, 
            "message_edit", 
            f"📝 **Message Edited in {before.channel.mention}**\n"
            f"**Author:** {before.author}\n"
            f"**Before:** {before.content}\n"
            f"**After:** {after.content}"
        )

    # =========================
    # 👥 MEMBER LOGGING
    # =========================
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Tracking Nickname Changes
        if before.nick != after.nick:
            await dispatch_log(
                before.guild, 
                "member_update", 
                f"🎨 **Nickname Changed**\n"
                f"**User:** {after.mention}\n"
                f"**Old:** `{before.nick or 'None'}`\n"
                f"**New:** `{after.nick or 'None'}`"
            )

        # Tracking Role Updates
        if len(before.roles) != len(after.roles):
            added = [r.mention for r in after.roles if r not in before.roles]
            removed = [r.mention for r in before.roles if r not in after.roles]
            
            action = f"✅ Added: {added[0]}" if added else f"❌ Removed: {removed[0]}"
            await dispatch_log(
                before.guild, 
                "role_update", 
                f"🎭 **Role Updated** for {after.mention}\n{action}"
            )

    # =========================
    # 🔊 VOICE LOGGING
    # =========================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel: return
        
        if before.channel is None:
            msg = f"📥 {member.mention} **joined** voice channel: `{after.channel.name}`"
        elif after.channel is None:
            msg = f"📤 {member.mention} **left** voice channel: `{before.channel.name}`"
        else:
            msg = f"🔄 {member.mention} **moved** from `{before.channel.name}` to `{after.channel.name}`"

        await dispatch_log(member.guild, "voice", msg)

async def setup(bot):
    await bot.add_cog(Events(bot))
