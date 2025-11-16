#!/usr/bin/env python3

import discord as dc
import os
import asyncio
from typing import Optional
from discord.ext import commands

from config import BotConfig
from utils.logger import Logger
from cogs.AdminCog import AdminCog
from cogs.FunCog import FunCog
from cogs.MusicCog import MusicCog


class MusicBot:
    """Main Discord Music Bot class."""
    
    def __init__(self) -> None:
        """Initialize the Discord Music Bot."""
        # Get token from config (env variables loaded in config.py)
        self.token: Optional[str] = BotConfig.get_env_var("TOKEN")
        
        if not self.token:
            Logger.log_error(Exception("TOKEN not found in environment"), "STARTUP")
            raise ValueError("Discord bot token not found. Please set TOKEN in .env file.")
        
        # Configure bot intents - Updated for discord.py 2.6.4
        intents = dc.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True
        
        # Create bot instance
        self.bot = commands.Bot(
            command_prefix=BotConfig.COMMAND_PREFIX,
            intents=intents,
            help_command=None,  # We'll use custom help command
            case_insensitive=BotConfig.CASE_INSENSITIVE
        )
        
        # Setup event handlers
        self.setup_events()
        
        # Run the bot
        asyncio.run(self.main())

    def setup_events(self) -> None:
        """Setup bot event handlers."""
        
        @self.bot.event
        async def on_ready() -> None:
            """Bot ready event handler."""
            Logger.log_info(
                f"Bot zalogowany jako {self.bot.user} (ID: {self.bot.user.id})",  # type: ignore
                "STARTUP"
            )
            Logger.log_info(f"Bot jest na {len(self.bot.guilds)} serwerach", "STARTUP")
        
        @self.bot.event
        async def on_guild_join(guild: dc.Guild) -> None:
            """Guild join event handler."""
            Logger.log_info(f"Dołączono do nowego serwera: {guild.name} (ID: {guild.id})", "GUILD_JOIN")
        
        @self.bot.event
        async def on_guild_remove(guild: dc.Guild) -> None:
            """Guild remove event handler."""
            Logger.log_info(f"Usunięto z serwera: {guild.name} (ID: {guild.id})", "GUILD_REMOVE")
    
    async def load_cogs(self) -> None:
        """Load all bot cogs."""
        try:
            await self.bot.add_cog(AdminCog(bot=self.bot))
            Logger.log_info("AdminCog załadowany", "COGS")
            
            await self.bot.add_cog(FunCog(bot=self.bot))
            Logger.log_info("FunCog załadowany", "COGS")
            
            music_cog = MusicCog(bot=self.bot)
            await self.bot.add_cog(music_cog)
            Logger.log_info("MusicCog załadowany", "COGS")
            
        except Exception as e:
            Logger.log_error(e, "LOAD_COGS")
            raise
    
    async def sync_slash_commands(self) -> None:
        """Sync slash commands for discord.py 2.6.4."""
        try:
            synced = await self.bot.tree.sync()
            Logger.log_info(f"Zsynchronizowano {len(synced)} slash commands", "SLASH_COMMANDS")
        except Exception as e:
            Logger.log_error(e, "SYNC_SLASH_COMMANDS")
    
    async def main(self) -> None:
        """Main bot startup routine."""
        try:
            # Ensure directories exist
            BotConfig.create_directories()
            Logger.log_info("Katalogi zostały utworzone/sprawdzone", "STARTUP")
            
            # Load cogs
            await self.load_cogs()
            
            # Setup slash commands sync on ready
            @self.bot.event
            async def on_ready() -> None:
                Logger.log_info(
                    f"Bot zalogowany jako {self.bot.user} (ID: {self.bot.user.id})",  # type: ignore
                    "STARTUP"
                )
                Logger.log_info(f"Bot jest na {len(self.bot.guilds)} serwerach", "STARTUP")
                
                # Sync slash commands
                await self.sync_slash_commands()
                Logger.log_info("Bot gotowy do użycia!", "STARTUP")
            
            # Start the bot
            Logger.log_info("Uruchamianie bota...", "STARTUP")
            await self.bot.start(self.token)  # type: ignore
            
        except Exception as e:
            Logger.log_error(e, "MAIN_STARTUP")
            raise


def main() -> None:
    """Entry point for the bot."""
    try:
        MusicBot()
    except KeyboardInterrupt:
        Logger.log_info("Bot został zatrzymany przez użytkownika", "SHUTDOWN")
    except Exception as e:
        Logger.log_error(e, "FATAL_ERROR")
        raise

if __name__ == "__main__":
    main()
