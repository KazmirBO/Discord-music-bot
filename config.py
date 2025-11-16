#!/usr/bin/env python3

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables at module import
load_dotenv()

class BotConfig:
    """Centralized configuration for the Discord Music Bot."""
    
    # Bot Configuration
    COMMAND_PREFIX = "+"
    CASE_INSENSITIVE = True
    
    # Rate Limiting
    COOLDOWN_TIME = 3  # seconds
    MAX_QUEUE_PER_USER = 15
    
    # Cache Configuration
    SEARCH_CACHE_EXPIRY = 3600  # 1 hour in seconds
    
    # Directory Paths
    FILES_DIR = "./files"
    PLAYLISTS_DIR = "./playlists"
    LOGS_DIR = "./logs"
    
    # Audio Configuration - Simplified for reliability
    YDL_OPTS: Dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": f"{FILES_DIR}/%(id)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        # Basic retry logic
        "extractor_retries": 3,
        "fragment_retries": 3,
        # Modern user agent
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
    }
    
    FFMPEG_OPTS: Dict[str, str] = {
        "before_options": "-nostdin",
        "options": "-vn",
    }
    
    # URLs
    YOUTUBE_BASE_URL = "https://www.youtube.com/watch?v="
    
    # Embed Colors - Updated with more Discord-friendly colors
    COLORS = {
        "success": 0x00FF7F,      # Spring Green
        "error": 0xFF4444,        # Light Red
        "info": 0x5865F2,         # Discord Blurple
        "warning": 0xFFA500,      # Orange
        "purple": 0x9966FF,       # Purple
        "playing": 0x1DB954,      # Spotify Green
        "queue": 0x7289DA,        # Discord Blue
        "auto_dj": 0xFF6B9D       # Pink
    }
    
    # New Features for Updated Libraries
    # Discord.py 2.6.4 Features
    MAX_EMBED_LENGTH = 4096
    MAX_EMBED_FIELDS = 25
    MAX_FIELD_VALUE_LENGTH = 1024
    
    # yt-dlp 2025.11.12 Features
    ENABLE_SPONSORBLOCK = False  # Disabled to avoid download issues
    ENABLE_CHAPTERS = False
    MAX_DOWNLOAD_SIZE = "100M"  # Reduced for faster downloads
    
    # File Extensions
    AUDIO_EXTENSIONS = [".webm", ".mp3", ".mp4", ".m4a"]
    
    @classmethod
    def create_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        directories = [cls.FILES_DIR, cls.PLAYLISTS_DIR, cls.LOGS_DIR]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    @classmethod
    def get_env_var(cls, var_name: str, default: str = "") -> str:
        """Get environment variable with optional default."""
        return os.getenv(var_name, default)