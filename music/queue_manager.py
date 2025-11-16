#!/usr/bin/env python3

from typing import Dict, List, Optional, Set
from collections import defaultdict
from music.track import Track

class QueueManager:
    """Manages music queues for different guilds."""
    
    def __init__(self):
        self.queues: Dict[int, List[Track]] = {}
        self.current_tracks: Dict[int, Optional[Track]] = {}
        self.loop_status: Dict[int, bool] = {}
    
    def add_track(self, guild_id: int, track: Track) -> None:
        """Add track to guild's queue."""
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        self.queues[guild_id].append(track)
    
    def add_tracks(self, guild_id: int, tracks: List[Track]) -> None:
        """Add multiple tracks to guild's queue."""
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        self.queues[guild_id].extend(tracks)
    
    def get_next_track(self, guild_id: int, position: int = 0) -> Optional[Track]:
        """Get next track from queue and remove it."""
        if guild_id not in self.queues or not self.queues[guild_id]:
            return None
        
        if position >= len(self.queues[guild_id]):
            return None
        
        return self.queues[guild_id].pop(position)
    
    def remove_track(self, guild_id: int, position: int) -> Optional[Track]:
        """Remove track at specific position."""
        if (guild_id not in self.queues or 
            position >= len(self.queues[guild_id]) or 
            position < 0):
            return None
        
        return self.queues[guild_id].pop(position)
    
    def get_queue(self, guild_id: int) -> List[Track]:
        """Get guild's current queue."""
        return self.queues.get(guild_id, [])
    
    def get_queue_length(self, guild_id: int) -> int:
        """Get length of guild's queue."""
        return len(self.queues.get(guild_id, []))
    
    def clear_queue(self, guild_id: int) -> None:
        """Clear guild's queue."""
        if guild_id in self.queues:
            self.queues[guild_id].clear()
    
    def set_current_track(self, guild_id: int, track: Optional[Track]) -> None:
        """Set currently playing track."""
        self.current_tracks[guild_id] = track
    
    def get_current_track(self, guild_id: int) -> Optional[Track]:
        """Get currently playing track."""
        return self.current_tracks.get(guild_id)
    
    def set_loop_status(self, guild_id: int, status: bool) -> None:
        """Set loop status for guild."""
        self.loop_status[guild_id] = status
    
    def is_looping(self, guild_id: int) -> bool:
        """Check if guild has looping enabled."""
        return self.loop_status.get(guild_id, False)
    
    def toggle_loop(self, guild_id: int) -> bool:
        """Toggle loop status and return new status."""
        current_status = self.loop_status.get(guild_id, False)
        self.loop_status[guild_id] = not current_status
        return self.loop_status[guild_id]
    
    def get_all_active_track_ids(self) -> Set[str]:
        """Get all active track IDs across all guilds."""
        active_ids = set()
        
        # Add IDs from queues
        for queue in self.queues.values():
            for track in queue:
                active_ids.add(track.id)
        
        # Add IDs from current tracks
        for track in self.current_tracks.values():
            if track:
                active_ids.add(track.id)
        
        return active_ids
    
    def has_content(self, guild_id: int) -> bool:
        """Check if guild has any tracks in queue or currently playing."""
        has_queue = guild_id in self.queues and bool(self.queues[guild_id])
        has_current = guild_id in self.current_tracks and bool(self.current_tracks[guild_id])
        return has_queue or has_current