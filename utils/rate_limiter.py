#!/usr/bin/env python3

import time
from collections import defaultdict
from typing import Dict, Tuple, DefaultDict
from config import BotConfig

class RateLimiter:
    """Handles rate limiting and user quotas for bot commands."""
    
    def __init__(self):
        self.user_cooldowns: Dict[str, float] = {}
        self.user_queue_items: DefaultDict[int, DefaultDict[int, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.cooldown_time = BotConfig.COOLDOWN_TIME
        self.max_queue_per_user = BotConfig.MAX_QUEUE_PER_USER
    
    def check_user_limits(self, user_id: int, guild_id: int, command_type: str = "play") -> Tuple[bool, str]:
        """
        Check if user can execute a command based on cooldowns and limits.
        
        Returns:
            Tuple[bool, str]: (can_proceed, error_message)
        """
        current_time = time.time()
        
        # Check cooldown
        cooldown_key = f"{user_id}:{guild_id}:{command_type}"
        if cooldown_key in self.user_cooldowns:
            last_use = self.user_cooldowns[cooldown_key]
            if current_time - last_use < self.cooldown_time:
                return (
                    False,
                    f"Spokojnie! Poczekaj {self.cooldown_time} sekund między komendami."
                )
        
        # Update last use time
        self.user_cooldowns[cooldown_key] = current_time
        
        # Check queue limits for play commands
        if command_type == "play":
            current_count = self.user_queue_items[guild_id][user_id]
            if current_count >= self.max_queue_per_user:
                return (
                    False,
                    f"Osiągnąłeś limit {self.max_queue_per_user} utworów w kolejce. "
                    f"Poczekaj, aż niektóre zostaną odtworzone."
                )
        
        return True, ""
    
    def add_tracks_to_user_count(self, user_id: int, guild_id: int, count: int = 1) -> None:
        """Add tracks to user's queue count."""
        self.user_queue_items[guild_id][user_id] += count
    
    def remove_tracks_from_user_count(self, user_id: int, guild_id: int, count: int = 1) -> None:
        """Remove tracks from user's queue count."""
        self.user_queue_items[guild_id][user_id] = max(
            0, self.user_queue_items[guild_id][user_id] - count
        )
    
    def clear_user_queue_count(self, guild_id: int, user_id: int = None) -> None:
        """Clear queue count for specific user or all users in guild."""
        if user_id is not None:
            self.user_queue_items[guild_id][user_id] = 0
        else:
            self.user_queue_items[guild_id].clear()
    
    def get_user_queue_count(self, user_id: int, guild_id: int) -> int:
        """Get current queue count for user."""
        return self.user_queue_items[guild_id][user_id]
    
    def can_add_tracks(self, user_id: int, guild_id: int, track_count: int) -> Tuple[bool, int]:
        """
        Check if user can add specified number of tracks.
        
        Returns:
            Tuple[bool, int]: (can_add_all, max_addable_count)
        """
        current_count = self.user_queue_items[guild_id][user_id]
        max_addable = max(0, self.max_queue_per_user - current_count)
        
        if track_count <= max_addable:
            return True, track_count
        else:
            return False, max_addable