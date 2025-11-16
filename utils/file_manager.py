#!/usr/bin/env python3

import os
import shutil
from typing import Set, Optional
from config import BotConfig
from utils.logger import Logger

class FileManager:
    """Handles file operations and cleanup for downloaded audio files."""
    
    @staticmethod
    def cleanup_files(file_id: Optional[str] = None, active_ids: Optional[Set[str]] = None) -> None:
        """
        Clean up audio files. Can remove single file or all unused files.
        
        Args:
            file_id: Specific file ID to remove
            active_ids: Set of currently active file IDs to preserve
        """
        if file_id:
            FileManager._remove_single_file(file_id)
        elif active_ids is not None:
            FileManager._remove_unused_files(active_ids)
        else:
            Logger.log_info("No cleanup parameters provided", "FILE_MANAGER")
    
    @staticmethod
    def _remove_single_file(file_id: str) -> None:
        """Remove a single audio file by ID."""
        try:
            for ext in BotConfig.AUDIO_EXTENSIONS:
                file_path = f"{BotConfig.FILES_DIR}/{file_id}{ext}"
                if os.path.exists(file_path):
                    os.remove(file_path)
                    Logger.log_info(f"Removed file: {file_path}", "FILE_CLEANUP")
                    break
        except Exception as e:
            Logger.log_error(e, "FILE_CLEANUP")
    
    @staticmethod
    def _remove_unused_files(active_ids: Set[str]) -> None:
        """Remove all files not in the active IDs set."""
        if not os.path.exists(BotConfig.FILES_DIR):
            return
        
        removed_count = 0
        try:
            for file in os.listdir(BotConfig.FILES_DIR):
                # Check if file has audio extension
                if any(file.endswith(ext) for ext in BotConfig.AUDIO_EXTENSIONS):
                    file_id = file.split(".")[0]
                    if file_id not in active_ids:
                        file_path = f"{BotConfig.FILES_DIR}/{file}"
                        os.remove(file_path)
                        removed_count += 1
            
            if removed_count > 0:
                Logger.log_info(f"Removed {removed_count} unused audio files", "FILE_CLEANUP")
                
        except Exception as e:
            Logger.log_error(e, "FILE_CLEANUP")
    
    @staticmethod
    def ensure_directories_exist() -> None:
        """Ensure all required directories exist."""
        BotConfig.create_directories()
    
    @staticmethod
    def get_file_path(file_id: str, extension: str = ".webm") -> str:
        """Get full path for audio file."""
        return f"{BotConfig.FILES_DIR}/{file_id}{extension}"
    
    @staticmethod
    def file_exists(file_id: str) -> bool:
        """Check if audio file exists for given ID."""
        for ext in BotConfig.AUDIO_EXTENSIONS:
            if os.path.exists(f"{BotConfig.FILES_DIR}/{file_id}{ext}"):
                return True
        return False