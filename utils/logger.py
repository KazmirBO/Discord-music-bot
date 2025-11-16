#!/usr/bin/env python3

import os
import datetime as dt
from typing import Optional
from config import BotConfig

class Logger:
    """Centralized logging utility for the bot."""
    
    @staticmethod
    def log_error(error: Exception, context: Optional[str] = None) -> None:
        """Log error to file with timestamp and optional context."""
        if not os.path.exists(BotConfig.LOGS_DIR):
            os.makedirs(BotConfig.LOGS_DIR)
        
        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_msg = f"[{timestamp}] {error}"
        
        if context:
            error_msg = f"[{timestamp}] [{context}] {error}"
        
        try:
            with open(f"{BotConfig.LOGS_DIR}/errors.log", "a", encoding="utf-8") as f:
                f.write(f"{error_msg}\n")
        except Exception as log_error:
            print(f"Błąd podczas zapisywania do pliku logów: {log_error}")
    
    @staticmethod
    def log_info(message: str, context: Optional[str] = None) -> None:
        """Log info message to console and optionally to file."""
        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        
        if context:
            log_msg = f"[{timestamp}] [{context}] {message}"
        
        print(log_msg)
    
    @staticmethod
    def log_cache_cleanup(items_removed: int) -> None:
        """Log cache cleanup operations."""
        Logger.log_info(
            f"Wyczyszczono {items_removed} wygasłych elementów cache'u.",
            "CACHE_CLEANUP"
        )