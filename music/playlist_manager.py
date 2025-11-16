#!/usr/bin/env python3

import os
import json
import datetime as dt
from typing import List, Dict, Any, Optional
from music.track import Track
from config import BotConfig
from utils.logger import Logger

class PlaylistManager:
    """Manages saving and loading of playlists."""
    
    @staticmethod
    def save_playlist(name: str, tracks: List[Track], creator: str) -> bool:
        """
        Save playlist to file.
        
        Args:
            name: Playlist name
            tracks: List of tracks to save
            creator: Username of creator
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(BotConfig.PLAYLISTS_DIR):
                os.makedirs(BotConfig.PLAYLISTS_DIR)
            
            playlist_data = {
                "nazwa": name,
                "utworzony_przez": creator,
                "utworzony_dnia": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "utwory": [track.to_dict() for track in tracks]
            }
            
            file_path = f"{BotConfig.PLAYLISTS_DIR}/{name}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(playlist_data, f, ensure_ascii=False, indent=4)
            
            Logger.log_info(f"Playlist '{name}' saved with {len(tracks)} tracks", "PLAYLIST")
            return True
            
        except Exception as e:
            Logger.log_error(e, f"SAVE_PLAYLIST: {name}")
            return False
    
    @staticmethod
    def load_playlist(name: str) -> Optional[Dict[str, Any]]:
        """
        Load playlist from file.
        
        Args:
            name: Playlist name
            
        Returns:
            Playlist data dict or None if failed/not found
        """
        try:
            file_path = f"{BotConfig.PLAYLISTS_DIR}/{name}.json"
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                playlist_data = json.load(f)
            
            # Convert track dicts back to Track objects
            tracks = [Track.from_dict(track_data) for track_data in playlist_data.get("utwory", [])]
            playlist_data["utwory"] = tracks
            
            Logger.log_info(f"Playlist '{name}' loaded with {len(tracks)} tracks", "PLAYLIST")
            return playlist_data
            
        except Exception as e:
            Logger.log_error(e, f"LOAD_PLAYLIST: {name}")
            return None
    
    @staticmethod
    def get_playlist_list() -> List[Dict[str, Any]]:
        """
        Get list of all available playlists with metadata.
        
        Returns:
            List of playlist info dicts
        """
        playlists = []
        
        try:
            if not os.path.exists(BotConfig.PLAYLISTS_DIR):
                return playlists
            
            playlist_files = [f for f in os.listdir(BotConfig.PLAYLISTS_DIR) 
                            if f.endswith(".json")]
            
            for playlist_file in playlist_files:
                try:
                    name = playlist_file.replace(".json", "")
                    file_path = f"{BotConfig.PLAYLISTS_DIR}/{playlist_file}"
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    playlist_info = {
                        "name": name,
                        "track_count": len(data.get("utwory", [])),
                        "creator": data.get("utworzony_przez", "Unknown"),
                        "created_date": data.get("utworzony_dnia", "Unknown")
                    }
                    
                    playlists.append(playlist_info)
                    
                except Exception as e:
                    Logger.log_error(e, f"READ_PLAYLIST_INFO: {playlist_file}")
                    continue
            
        except Exception as e:
            Logger.log_error(e, "GET_PLAYLIST_LIST")
        
        return playlists
    
    @staticmethod
    def playlist_exists(name: str) -> bool:
        """Check if playlist exists."""
        file_path = f"{BotConfig.PLAYLISTS_DIR}/{name}.json"
        return os.path.exists(file_path)
    
    @staticmethod
    def delete_playlist(name: str) -> bool:
        """
        Delete playlist file.
        
        Args:
            name: Playlist name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = f"{BotConfig.PLAYLISTS_DIR}/{name}.json"
            
            if os.path.exists(file_path):
                os.remove(file_path)
                Logger.log_info(f"Playlist '{name}' deleted", "PLAYLIST")
                return True
            
            return False
            
        except Exception as e:
            Logger.log_error(e, f"DELETE_PLAYLIST: {name}")
            return False