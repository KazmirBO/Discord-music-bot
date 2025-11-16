#!/usr/bin/env python3

import datetime as dt
from typing import Dict, Any, Optional
from dataclasses import dataclass
from config import BotConfig

@dataclass
class Track:
    """Represents a music track with all its metadata."""
    
    url: str
    title: str
    uploader: str
    duration: int
    id: str
    user: str
    
    @classmethod
    def from_yt_info(cls, info: Dict[str, Any], username: str) -> 'Track':
        """Create Track from yt-dlp info dict with validation."""
        # Validate required fields
        required_fields = ['id', 'title', 'uploader', 'duration']
        for field in required_fields:
            if field not in info or info[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Ensure duration is a number
        duration = info['duration']
        if not isinstance(duration, (int, float)):
            try:
                duration = float(duration)
            except (ValueError, TypeError):
                duration = 0  # Default to 0 if conversion fails
        
        return cls(
            url=f"{BotConfig.YOUTUBE_BASE_URL}{info['id']}",
            title=str(info['title']),
            uploader=str(info['uploader']),
            duration=int(duration),
            id=str(info['id']),
            user=username
        )
    
    def get_duration_string(self) -> str:
        """Get formatted duration string."""
        return str(dt.timedelta(seconds=self.duration))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'title': self.title,
            'uploader': self.uploader,
            'duration': self.duration,
            'id': self.id,
            'user': self.user
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """Create Track from dictionary."""
        return cls(**data)