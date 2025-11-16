#!/usr/bin/env python3

import re
import time
import yt_dlp
from typing import Dict, Any, List, Optional, Tuple
from config import BotConfig
from utils.logger import Logger

class YouTubeDownloader:
    """Handles YouTube content extraction and caching with yt-dlp 2025.11.12 features."""
    
    def __init__(self):
        # Use simplified configuration for reliability
        opts = BotConfig.YDL_OPTS.copy()
        
        # Add file size limit if configured
        if hasattr(BotConfig, 'MAX_DOWNLOAD_SIZE') and BotConfig.MAX_DOWNLOAD_SIZE:
            opts["max_filesize"] = BotConfig.MAX_DOWNLOAD_SIZE
            
        self.ydl = yt_dlp.YoutubeDL(opts)
        self.search_cache: Dict[str, Tuple[float, Any]] = {}
        self.cache_expiry = BotConfig.SEARCH_CACHE_EXPIRY
    
    def is_youtube_link(self, text: str) -> bool:
        """Check if text is a YouTube URL."""
        pattern = re.compile(r"(https?://)?(www\.)?(youtube|youtu)\.(com|be)/.+$")
        return pattern.match(text) is not None
    
    def is_youtube_playlist_link(self, text: str) -> bool:
        """Check if text is a YouTube playlist URL."""
        pattern = re.compile(
            r"(https?://)?(www\.)?(youtube|youtu)\.(com|be)/playlist\?list=.+$"
        )
        return pattern.match(text) is not None
    
    def extract_info(self, url: str, download: bool = True) -> Optional[Dict[str, Any]]:
        """Extract information from URL with improved error handling and fallback mechanisms."""
        try:
            Logger.log_info(f"Extracting {'with download' if download else 'metadata only'}: {url}", "YOUTUBE")
            result = self.ydl.extract_info(url, download=download)
            if result:
                Logger.log_info(f"Successfully extracted: {result.get('title', 'Unknown')}", "YOUTUBE")
            return result
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a bot detection error
            if "sign in to confirm" in error_msg or "not a bot" in error_msg:
                Logger.log_warning("YouTube bot detection triggered, trying fallback method", "YOUTUBE")
                return self._try_fallback_extraction(url, download)
            
            # Check if it's a private/unavailable video
            elif "private video" in error_msg or "unavailable" in error_msg:
                Logger.log_warning(f"Video unavailable: {url}", "YOUTUBE")
                return None
            
            Logger.log_error(e, f"YOUTUBE_EXTRACT: {url}")
            return None
    
    def _try_fallback_extraction(self, url: str, download: bool = True) -> Optional[Dict[str, Any]]:
        """Try alternative extraction methods when bot detection is triggered."""
        try:
            # Create a new YDL instance with different options
            fallback_opts = BotConfig.YDL_OPTS.copy()
            
            # Use more flexible format selection for fallback
            fallback_opts["format"] = "worst[height<=360]/worstaudio/worst"
            
            # Use Android client as primary
            fallback_opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["android", "web_creator", "tv_embedded"],
                    "player_skip": ["webpage"],
                }
            }
            
            # Add more delays
            fallback_opts["sleep_interval"] = 1
            fallback_opts["sleep_interval_requests"] = 0.5
            
            with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                Logger.log_info(f"Fallback extraction attempt: {url}", "YOUTUBE")
                result = fallback_ydl.extract_info(url, download=download)
                if result:
                    Logger.log_info(f"Fallback successful: {result.get('title', 'Unknown')}", "YOUTUBE")
                return result
                
        except Exception as e:
            Logger.log_error(e, f"YOUTUBE_FALLBACK: {url}")
            
            # Try one more time with the most basic format
            try:
                basic_opts = {
                    "format": "worst",
                    "outtmpl": BotConfig.YDL_OPTS["outtmpl"],
                    "quiet": True,
                    "extractor_args": {
                        "youtube": {
                            "player_client": ["android"],
                        }
                    }
                }
                
                with yt_dlp.YoutubeDL(basic_opts) as basic_ydl:
                    Logger.log_info(f"Basic fallback attempt: {url}", "YOUTUBE")
                    result = basic_ydl.extract_info(url, download=download)
                    if result:
                        Logger.log_info(f"Basic fallback successful: {result.get('title', 'Unknown')}", "YOUTUBE")
                    return result
            except Exception as final_e:
                Logger.log_error(final_e, f"YOUTUBE_BASIC_FALLBACK: {url}")
                return None
    
    def search_youtube(self, query: str, max_results: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        Search YouTube and return results.
        Uses caching to avoid repeated API calls.
        """
        cache_key = f"{query}:{max_results}"
        
        # Check cache
        if cache_key in self.search_cache:
            cache_time, cache_data = self.search_cache[cache_key]
            if time.time() - cache_time < self.cache_expiry:
                return cache_data
        
        # Perform search
        try:
            search_query = f"ytsearch{max_results if max_results > 1 else ''}:'{query}'"
            result = self.ydl.extract_info(search_query, download=False)
            
            if result and 'entries' in result:
                entries = result['entries']
                # Cache the result
                self.search_cache[cache_key] = (time.time(), entries)
                return entries
            
        except Exception as e:
            Logger.log_error(e, f"YOUTUBE_SEARCH: {query}")
        
        return None
    
    def get_track_info(self, url_or_query: str) -> Optional[Dict[str, Any]]:
        """
        Get track info from URL or search query.
        Returns single track info or None if failed.
        """
        try:
            if self.is_youtube_link(url_or_query):
                # First get info without downloading for metadata
                result = self.extract_info(url_or_query, download=False)
                if result and not result.get('_type') == 'playlist':
                    # Then download the file
                    self.extract_info(url_or_query, download=True)
                    return result
                return result
            else:
                # Search and return first result
                results = self.search_youtube(url_or_query, 1)
                if results and len(results) > 0:
                    # Download the found track
                    track_info = results[0]
                    if track_info and 'id' in track_info:
                        # Download the actual file
                        self.extract_info(f"https://www.youtube.com/watch?v={track_info['id']}", download=True)
                    return track_info
                return None
        except Exception as e:
            Logger.log_error(e, f"GET_TRACK_INFO: {url_or_query}")
            return None
    
    def get_playlist_info(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """Get playlist information from URL."""
        if not self.is_youtube_playlist_link(url):
            return None
        
        try:
            result = self.extract_info(url, download=False)
            if result and 'entries' in result:
                return result['entries']
        except Exception as e:
            Logger.log_error(e, f"PLAYLIST_EXTRACT: {url}")
        
        return None
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries and return count of removed items."""
        current_time = time.time()
        expired_keys = []
        
        for key, (cache_time, _) in self.search_cache.items():
            if current_time - cache_time > self.cache_expiry:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.search_cache[key]
        
        return len(expired_keys)
    
    def get_similar_tracks(self, track_info: Dict[str, Any], count: int = 3) -> List[Dict[str, Any]]:
        """Get tracks similar to the provided track."""
        if not track_info:
            return []
        
        # Create search query from title and uploader
        query = f"{track_info.get('title', '')} {track_info.get('uploader', '')} podobne"
        
        try:
            results = self.search_youtube(query, count)
            if not results:
                return []
            
            # Filter out the original track
            current_id = track_info.get('id')
            similar_tracks = []
            
            for track in results:
                if track.get('id') != current_id:
                    similar_tracks.append(track)
            
            return similar_tracks
            
        except Exception as e:
            Logger.log_error(e, f"SIMILAR_TRACKS: {track_info.get('title', 'unknown')}")
            return []