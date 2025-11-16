#!/usr/bin/env python3

import discord as dc
from typing import Optional
from discord.ext import commands

class UserManager:
    """Utility class for user-related operations."""
    
    @staticmethod
    async def get_user_info(ctx: commands.Context) -> tuple[str, int]:
        """
        Get user display name and guild ID, cleaning up the command message.
        
        Returns:
            Tuple[str, int]: (username, guild_id)
        """
        await ctx.channel.purge(limit=1)
        return ctx.message.author.display_name, ctx.message.guild.id
    
    @staticmethod
    def get_user_id_from_name(username: str, guild_id: int, bot: commands.Bot) -> Optional[int]:
        """
        Get user ID from display name in a specific guild.
        
        Args:
            username: Display name to search for
            guild_id: Guild ID to search in
            bot: Bot instance
            
        Returns:
            User ID if found, None otherwise
        """
        guild = bot.get_guild(guild_id)
        if not guild:
            return None
        
        for member in guild.members:
            if member.display_name == username:
                return member.id
        
        return None
    
    @staticmethod
    async def get_voice_client(ctx: commands.Context, bot: commands.Bot) -> Optional[dc.VoiceClient]:
        """Get or create voice client for the context."""
        if not ctx.voice_client and ctx.author.voice:
            return await ctx.author.voice.channel.connect()
        return dc.utils.get(bot.voice_clients, guild=ctx.guild)
    
    @staticmethod
    def user_can_modify_track(ctx: commands.Context, track_owner: str) -> bool:
        """
        Check if user can modify a track (either owner or admin).
        
        Args:
            ctx: Command context
            track_owner: Username of track owner
            
        Returns:
            True if user can modify, False otherwise
        """
        is_admin = ctx.author.guild_permissions.administrator
        is_owner = track_owner == ctx.author.display_name
        return is_admin or is_owner