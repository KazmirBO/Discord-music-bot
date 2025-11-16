#!/usr/bin/env python3

import discord as dc
import datetime as dt
import os
import lyricsgenius
from typing import Optional, List
from discord.ext import commands, tasks

from config import BotConfig
from utils.rate_limiter import RateLimiter
from utils.user_manager import UserManager
from utils.file_manager import FileManager
from utils.logger import Logger
from music.track import Track
from music.queue_manager import QueueManager
from music.youtube_downloader import YouTubeDownloader
from music.playlist_manager import PlaylistManager

class MusicCog(commands.Cog):
    """Refactored Music Cog with improved structure and separation of concerns."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        # Initialize managers and utilities
        self.rate_limiter = RateLimiter()
        self.queue_manager = QueueManager()
        self.youtube_downloader = YouTubeDownloader()
        
        # Voice clients per guild
        self.voice_clients: dict[int, Optional[dc.VoiceClient]] = {}
        
        # Music loop tasks per guild
        self.music_loops: dict[int, Optional[tasks.Loop]] = {}
        
        # AutoDJ settings per guild
        self.auto_dj_enabled: dict[int, bool] = {}
        
        # Initialize Genius API for lyrics
        self.genius = self._initialize_genius()
        
        # Start cache cleanup task
        self.cache_cleanup_task.start()
        
        # Ensure directories exist
        FileManager.ensure_directories_exist()
    
    def _initialize_genius(self) -> Optional[lyricsgenius.Genius]:
        """Initialize Genius API client with lyricsgenius 3.7.5 features."""
        try:
            genius_token = BotConfig.get_env_var("GENIUS_TOKEN")
            if genius_token:
                genius = lyricsgenius.Genius(genius_token)
                # Configure for better performance with new version
                genius.timeout = 15
                genius.sleep_time = 0.5
                genius.retries = 3
                genius.remove_section_headers = True
                genius.skip_non_songs = True
                genius.excluded_terms = ["(Remix)", "(Instrumental)", "(Cover)"]
                return genius
        except Exception as e:
            Logger.log_error(e, "GENIUS_INIT")
        return None
    
    def _check_user_limits(self, ctx: commands.Context, command_type: str = "play") -> tuple[bool, str]:
        """Check user rate limits and return result."""
        return self.rate_limiter.check_user_limits(
            ctx.author.id, ctx.guild.id, command_type
        )
    
    async def _get_voice_client(self, ctx: commands.Context) -> Optional[dc.VoiceClient]:
        """Get or create voice client for the guild."""
        guild_id = ctx.guild.id
        
        if not ctx.voice_client and ctx.author.voice:
            self.voice_clients[guild_id] = await ctx.author.voice.channel.connect()
        else:
            self.voice_clients[guild_id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        
        return self.voice_clients[guild_id]
    
    def _create_track_embed(self, title: str, track: Track, color: int = None) -> dc.Embed:
        """Create enhanced embed for track information using updated discord.py features."""
        # Use appropriate color based on context
        if "Teraz odtwarzane" in title:
            embed_color = color or BotConfig.COLORS["playing"]
        elif "Dodano" in title:
            embed_color = color or BotConfig.COLORS["success"]
        else:
            embed_color = color or BotConfig.COLORS["info"]
            
        embed = dc.Embed(
            title=f"🎵 {title}",
            description=f"**{track.title}**",
            color=embed_color,
            timestamp=dc.utils.utcnow()  # Updated method for discord.py 2.6.4
        )
        
        # Enhanced field layout with emojis
        embed.add_field(name="👤 Dodał", value=track.user, inline=True)
        embed.add_field(name="📺 Kanał", value=track.uploader, inline=True)
        embed.add_field(name="⏱️ Czas", value=track.get_duration_string(), inline=True)
        
        # Add URL as clickable link
        embed.add_field(name="🔗 Link", value=f"[Otwórz w YouTube]({track.url})", inline=False)
        
        # Add footer with bot info
        embed.set_footer(text="Discord Music Bot", icon_url="https://cdn.discordapp.com/emojis/1234567890123456789.png")
        
        return embed
    
    def _create_queue_embed(self, guild_id: int) -> dc.Embed:
        """Create enhanced embed showing current queue status."""
        embed = dc.Embed(
            title="🎼 Kolejka odtwarzania",
            color=BotConfig.COLORS["queue"],
            timestamp=dc.utils.utcnow()
        )
        
        # Current track
        current = self.queue_manager.get_current_track(guild_id)
        if current:
            progress_info = (
                f"**{current.title}**\n"
                f"📺 {current.uploader}\n"
                f"⏱️ {current.get_duration_string()}\n"
                f"👤 {current.user}\n"
                f"🔗 [Link]({current.url})"
            )
            embed.add_field(name="🎵 Teraz gra:", value=progress_info, inline=False)
        
        # Queue with pagination support
        queue = self.queue_manager.get_queue(guild_id)
        if queue:
            # Limit to first 10 tracks to prevent embed overflow
            displayed_tracks = queue[:10]
            queue_info = []
            
            for i, track in enumerate(displayed_tracks, start=1):
                # Truncate long titles
                title = track.title[:50] + "..." if len(track.title) > 50 else track.title
                queue_info.append(
                    f"**{i}.** {title}\n"
                    f"⏱️ {track.get_duration_string()} | 👤 {track.user}"
                )
            
            embed.add_field(
                name=f"📋 Następne utwory ({len(queue)} w kolejce):",
                value="\n\n".join(queue_info) if queue_info else "Brak utworów",
                inline=False
            )
            
            if len(queue) > 10:
                embed.add_field(
                    name="ℹ️ Informacja:",
                    value=f"Pokazano 10 z {len(queue)} utworów w kolejce",
                    inline=False
                )
        else:
            embed.add_field(name="📋 Kolejka:", value="Pusta", inline=False)
        
        # Add loop status
        if self.queue_manager.is_looping(guild_id):
            embed.add_field(name="🔄", value="Zapętlanie włączone", inline=True)
        
        # Add AutoDJ status
        if self.auto_dj_enabled.get(guild_id, True):
            embed.add_field(name="🎧", value="AutoDJ aktywny", inline=True)
        
        embed.set_footer(text="Discord Music Bot • Użyj +help aby zobaczyć komendy")
        
        return embed
    
    async def _handle_track_addition(self, ctx: commands.Context, url_or_query: str) -> None:
        """Handle adding single track or playlist to queue."""
        username, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "play")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        # Check if it's a playlist
        if self.youtube_downloader.is_youtube_playlist_link(url_or_query):
            await self._handle_playlist_addition(ctx, url_or_query, username, guild_id)
        else:
            await self._handle_single_track_addition(ctx, url_or_query, username, guild_id)
    
    async def _handle_single_track_addition(self, ctx: commands.Context, url_or_query: str, username: str, guild_id: int) -> None:
        """Handle adding single track to queue."""
        try:
            # Show processing message for longer operations
            processing_embed = dc.Embed(
                title="🔍 Przetwarzanie",
                description=f"Pobieranie informacji o: **{url_or_query[:50]}...**",
                color=BotConfig.COLORS["info"]
            )
            processing_msg = await ctx.send(embed=processing_embed)
            
            track_info = self.youtube_downloader.get_track_info(url_or_query)
            if not track_info:
                error_embed = dc.Embed(
                    title="❌ Błąd",
                    description="Nie udało się pobrać informacji o utworze. Sprawdź czy link jest poprawny.",
                    color=BotConfig.COLORS["error"]
                )
                await processing_msg.edit(embed=error_embed)
                return
            
            track = Track.from_yt_info(track_info, username)
            
            # Add to queue and user count
            self.queue_manager.add_track(guild_id, track)
            self.rate_limiter.add_tracks_to_user_count(ctx.author.id, guild_id, 1)
            
            # Send confirmation
            embed = self._create_track_embed("Dodano", track)
            await processing_msg.edit(embed=embed)
            
            # Start playing if nothing is playing
            voice_client = await self._get_voice_client(ctx)
            if voice_client and not voice_client.is_playing():
                await self._play_next_track(ctx)
                
        except ValueError as e:
            error_embed = dc.Embed(
                title="❌ Błąd danych",
                description=f"Problem z metadanymi utworu: {str(e)}",
                color=BotConfig.COLORS["error"]
            )
            if 'processing_msg' in locals():
                await processing_msg.edit(embed=error_embed)
            else:
                await ctx.send(embed=error_embed)
            Logger.log_error(e, f"TRACK_CREATION: {url_or_query}")
            
        except Exception as e:
            error_embed = dc.Embed(
                title="❌ Nieoczekiwany błąd",
                description="Wystąpił problem podczas przetwarzania utworu.",
                color=BotConfig.COLORS["error"]
            )
            if 'processing_msg' in locals():
                await processing_msg.edit(embed=error_embed)
            else:
                await ctx.send(embed=error_embed)
            Logger.log_error(e, f"TRACK_ADDITION: {url_or_query}")
    
    async def _handle_playlist_addition(self, ctx: commands.Context, playlist_url: str, username: str, guild_id: int) -> None:
        """Handle adding playlist to queue."""
        playlist_info = self.youtube_downloader.get_playlist_info(playlist_url)
        if not playlist_info:
            await ctx.send("❌ Nie udało się pobrać playlisty.")
            return
        
        # Check user limits for playlist
        track_count = len(playlist_info)
        can_add_all, max_addable = self.rate_limiter.can_add_tracks(
            ctx.author.id, guild_id, track_count
        )
        
        if not can_add_all and max_addable == 0:
            await ctx.send(f"⚠️ Osiągnąłeś limit utworów w kolejce.")
            return
        
        # Add tracks (limited if necessary)
        tracks_to_add = playlist_info[:max_addable] if not can_add_all else playlist_info
        tracks = [Track.from_yt_info(info, username) for info in tracks_to_add]
        
        self.queue_manager.add_tracks(guild_id, tracks)
        self.rate_limiter.add_tracks_to_user_count(ctx.author.id, guild_id, len(tracks))
        
        # Send confirmation
        embed = dc.Embed(title="Dodano playlistę", color=BotConfig.COLORS["success"])
        embed.add_field(name="Kto dodał", value=username, inline=True)
        embed.add_field(name="Utworów dodano", value=str(len(tracks)), inline=True)
        
        if not can_add_all:
            embed.add_field(
                name="Uwaga", 
                value=f"Dodano tylko {len(tracks)} z {track_count} utworów (limit użytkownika)", 
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        # Start playing if nothing is playing
        voice_client = await self._get_voice_client(ctx)
        if voice_client and not voice_client.is_playing():
            await self._play_next_track(ctx)
    
    async def _play_next_track(self, ctx: commands.Context, position: int = 0) -> None:
        """Play next track from queue."""
        guild_id = ctx.guild.id
        
        # Get current track for cleanup
        old_track = self.queue_manager.get_current_track(guild_id)
        
        # Get next track
        next_track = self.queue_manager.get_next_track(guild_id, position)
        
        if next_track:
            # Update current track
            self.queue_manager.set_current_track(guild_id, next_track)
            
            # Update user count
            user_id = UserManager.get_user_id_from_name(next_track.user, guild_id, self.bot)
            if user_id:
                self.rate_limiter.remove_tracks_from_user_count(user_id, guild_id, 1)
            
            # Play the track
            voice_client = self.voice_clients[guild_id]
            if voice_client:
                audio_source = dc.FFmpegPCMAudio(
                    FileManager.get_file_path(next_track.id),
                    **BotConfig.FFMPEG_OPTS
                )
                voice_client.play(audio_source)
                
                # Send now playing message
                embed = self._create_track_embed("Teraz odtwarzane", next_track)
                await ctx.send(embed=embed)
                
                # Start music loop
                await self._start_music_loop(ctx)
                
                # Clean up old file
                if old_track:
                    FileManager.cleanup_files(old_track.id)
                
                # Check for AutoDJ
                await self._check_auto_dj(ctx)
        else:
            # No more tracks, disconnect
            self.queue_manager.set_current_track(guild_id, None)
            if guild_id in self.voice_clients and self.voice_clients[guild_id]:
                await self.voice_clients[guild_id].disconnect()
            
            # Clean up all files
            active_ids = self.queue_manager.get_all_active_track_ids()
            FileManager.cleanup_files(active_ids=active_ids)
    
    async def _start_music_loop(self, ctx: commands.Context) -> None:
        """Start or restart music loop for guild."""
        guild_id = ctx.guild.id
        
        if guild_id in self.music_loops and self.music_loops[guild_id]:
            if self.music_loops[guild_id].is_running():
                self.music_loops[guild_id].restart(ctx)
            else:
                self.music_loops[guild_id].start(ctx)
        else:
            self.music_loops[guild_id] = self.music_loop
            self.music_loops[guild_id].start(ctx)
    
    async def _check_auto_dj(self, ctx: commands.Context) -> None:
        """Check if AutoDJ should add similar tracks."""
        guild_id = ctx.guild.id
        
        if not self.auto_dj_enabled.get(guild_id, True):
            return
        
        if self.queue_manager.get_queue_length(guild_id) < 2:
            current = self.queue_manager.get_current_track(guild_id)
            if current:
                similar_tracks = self.youtube_downloader.get_similar_tracks(
                    current.to_dict(), count=3
                )
                
                if similar_tracks:
                    await ctx.send("🎵 Dodaję podobne utwory do kolejki...")
                    
                    tracks = [Track.from_yt_info(info, "AutoDJ 🤖") for info in similar_tracks]
                    self.queue_manager.add_tracks(guild_id, tracks)
                    
                    embed = dc.Embed(
                        title="Dodano podobne utwory",
                        description=f"Dodano {len(tracks)} podobnych utworów do kolejki.",
                        color=BotConfig.COLORS["purple"]
                    )
                    await ctx.send(embed=embed)
    
    @tasks.loop(seconds=5.0)
    async def music_loop(self, ctx: commands.Context) -> None:
        """Music loop to handle track progression."""
        guild_id = ctx.guild.id
        voice_client = self.voice_clients.get(guild_id)
        
        if voice_client and not voice_client.is_playing() and not voice_client.is_paused():
            # Handle looping
            if self.queue_manager.is_looping(guild_id):
                current = self.queue_manager.get_current_track(guild_id)
                if current:
                    # Add current track back to beginning of queue
                    queue = self.queue_manager.get_queue(guild_id)
                    queue.insert(0, current)
            
            await self._play_next_track(ctx)
    
    @tasks.loop(hours=1)
    async def cache_cleanup_task(self) -> None:
        """Clean up expired cache entries."""
        removed_count = self.youtube_downloader.clear_expired_cache()
        if removed_count > 0:
            Logger.log_cache_cleanup(removed_count)
    
    # Command implementations (Traditional prefix commands)
    @commands.command(pass_context=True, aliases=["p", "play"])
    async def play_music(self, ctx: commands.Context, *, url: str) -> None:
        """Play music from URL or search query."""
        if not ctx.author.voice:
            embed = dc.Embed(
                title="❌ Błąd",
                description="Najpierw dołącz do kanału głosowego!",
                color=BotConfig.COLORS["error"]
            )
            await ctx.send(embed=embed)
            return
        
        await self._handle_track_addition(ctx, url)
    
    # Modern Slash Commands (discord.py 2.6.4)
    @dc.app_commands.command(name="play", description="Odtwórz muzykę z YouTube")
    @dc.app_commands.describe(query="URL YouTube lub nazwa utworu do wyszukania")
    async def slash_play(self, interaction: dc.Interaction, query: str) -> None:
        """Slash command version of play."""
        if not interaction.user.voice:
            embed = dc.Embed(
                title="❌ Błąd",
                description="Najpierw dołącz do kanału głosowego!",
                color=BotConfig.COLORS["error"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Create a mock context for compatibility
        ctx = await self.bot.get_context(interaction)
        await self._handle_track_addition(ctx, query)
        
        # Send confirmation
        embed = dc.Embed(
            title="🎵 Przetwarzanie",
            description=f"Dodaję do kolejki: **{query}**",
            color=BotConfig.COLORS["info"]
        )
        await interaction.followup.send(embed=embed)
    
    @dc.app_commands.command(name="queue", description="Pokaż aktualną kolejkę odtwarzania")
    async def slash_queue(self, interaction: dc.Interaction) -> None:
        """Slash command version of queue."""
        await interaction.response.defer()
        
        guild_id = interaction.guild.id
        if self.queue_manager.has_content(guild_id):
            embed = self._create_queue_embed(guild_id)
            await interaction.followup.send(embed=embed)
        else:
            embed = dc.Embed(
                title="📋 Kolejka odtwarzania",
                description="Kolejka jest pusta",
                color=BotConfig.COLORS["info"]
            )
            await interaction.followup.send(embed=embed)
    
    @dc.app_commands.command(name="skip", description="Pomiń aktualny utwór")
    async def slash_skip(self, interaction: dc.Interaction) -> None:
        """Slash command version of skip."""
        await interaction.response.defer()
        
        guild_id = interaction.guild.id
        voice_client = self.voice_clients.get(guild_id)
        
        if not voice_client:
            embed = dc.Embed(
                title="❌ Błąd",
                description="Bot nie jest połączony z kanałem głosowym",
                color=BotConfig.COLORS["error"]
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        if voice_client.is_playing():
            voice_client.stop()
            embed = dc.Embed(
                title="⏭️ Pominięto",
                description="Pominięto aktualny utwór",
                color=BotConfig.COLORS["success"]
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = dc.Embed(
                title="❌ Błąd",
                description="Obecnie nic nie jest odtwarzane",
                color=BotConfig.COLORS["error"]
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @commands.command(pass_context=True, aliases=["f", "find"])
    async def find_music(self, ctx: commands.Context, *, query: str) -> None:
        """Search for music tracks."""
        username, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "find")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        results = self.youtube_downloader.search_youtube(query, 5)
        if not results:
            await ctx.send("❌ Nie znaleziono wyników.")
            return
        
        embed = dc.Embed(
            title="Wybierz link interesującego ciebie utworu:",
            color=dc.Colour.random()
        )
        embed.add_field(name="Kto szukał", value=username, inline=True)
        
        for track_info in results:
            duration_str = str(dt.timedelta(seconds=track_info.get('duration', 0)))
            embed.add_field(
                name=f"{track_info['title']}: {duration_str}",
                value=f"{BotConfig.YOUTUBE_BASE_URL}{track_info['id']}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(pass_context=False, aliases=["pr", "pause", "resume"])
    async def pause_resume(self, ctx: commands.Context) -> None:
        """Pause or resume music playback."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "pause")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")
            return
        
        if voice_client.is_playing():
            voice_client.pause()
            await ctx.send("Utwór został wstrzymany.")
        elif voice_client.is_paused():
            voice_client.resume()
            await ctx.send("Utwór został wznowiony!")
        else:
            await ctx.send("Wystąpił błąd! Nie ma czego wstrzymać/wznowić.")
    
    @commands.command(pass_context=True, aliases=["sk", "skip"])
    async def skip_track(self, ctx: commands.Context, position: int = 1) -> None:
        """Skip to next track or specific position in queue."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "skip")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")
            return
        
        queue_length = self.queue_manager.get_queue_length(guild_id)
        if queue_length < position:
            await ctx.send("Kolejka jest pusta lub pozycja jest nieprawidłowa.")
            return
        
        if voice_client.is_playing():
            voice_client.stop()
        
        await self._play_next_track(ctx, position - 1)
    
    @commands.command(pass_context=False, aliases=["q", "queue"])
    async def show_queue(self, ctx: commands.Context) -> None:
        """Display current music queue."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        if self.queue_manager.has_content(guild_id):
            embed = self._create_queue_embed(guild_id)
            await ctx.send(embed=embed)
        else:
            await ctx.send("Kolejka jest pusta.")
    
    @commands.command(pass_context=True, aliases=["dl", "delete"])
    async def delete_from_queue(self, ctx: commands.Context, position: int = None) -> None:
        """Delete track from queue."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "delete")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        if position is None:
            await ctx.send("Podaj pozycję do usunięcia!")
            return
        
        queue = self.queue_manager.get_queue(guild_id)
        if not queue or position > len(queue) or position < 1:
            await ctx.send("Wybrałeś zły numer.")
            return
        
        # Check permissions
        track_to_delete = queue[position - 1]
        if not UserManager.user_can_modify_track(ctx, track_to_delete.user):
            await ctx.send("⚠️ Możesz usuwać tylko swoje utwory z kolejki!")
            return
        
        # Remove track
        removed_track = self.queue_manager.remove_track(guild_id, position - 1)
        if removed_track:
            # Update user count
            user_id = UserManager.get_user_id_from_name(removed_track.user, guild_id, self.bot)
            if user_id:
                self.rate_limiter.remove_tracks_from_user_count(user_id, guild_id, 1)
            
            embed = self._create_track_embed("Usunięto z kolejki", removed_track)
            await ctx.send(embed=embed)
    
    @commands.command(pass_context=False, aliases=["s", "stop"])
    async def stop_music(self, ctx: commands.Context) -> None:
        """Stop music and clear queue."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "stop")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        voice_client = self.voice_clients.get(guild_id)
        if voice_client:
            voice_client.stop()
        
        self.queue_manager.clear_queue(guild_id)
        self.queue_manager.set_current_track(guild_id, None)
        self.rate_limiter.clear_user_queue_count(guild_id)
        
        await ctx.send("Zatrzymano odtwarzanie i wyczyszczono kolejkę.")
    
    @commands.command(pass_context=False, aliases=["d", "disconnect"])
    async def disconnect_bot(self, ctx: commands.Context) -> None:
        """Disconnect bot from voice channel."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "disconnect")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        voice_client = self.voice_clients.get(guild_id)
        if voice_client:
            await voice_client.disconnect()
            self.queue_manager.clear_queue(guild_id)
            self.queue_manager.set_current_track(guild_id, None)
            self.rate_limiter.clear_user_queue_count(guild_id)
            await ctx.send("Rozłączono z kanału głosowego.")
        else:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")
    
    @commands.command(pass_context=True, aliases=["v", "volume"])
    async def set_volume(self, ctx: commands.Context, volume: int = None) -> None:
        """Set or display volume."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "volume")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")
            return
        
        if volume is None:
            current_volume = getattr(voice_client, "volume", 1.0) * 100
            await ctx.send(f"Aktualna głośność: {int(current_volume)}%")
            return
        
        if volume < 0 or volume > 200:
            await ctx.send("Głośność musi być między 0 a 200%")
            return
        
        voice_client.volume = volume / 100
        await ctx.send(f"Głośność ustawiona na {volume}%")
    
    @commands.command(pass_context=True, aliases=["l", "lyrics"])
    async def show_lyrics(self, ctx: commands.Context) -> None:
        """Show lyrics for currently playing track."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "lyrics")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        if not self.genius:
            await ctx.send("❌ Funkcja tekstów jest niedostępna - brak tokenu API Genius.")
            return
        
        current_track = self.queue_manager.get_current_track(guild_id)
        if not current_track:
            await ctx.send("Obecnie nic nie jest odtwarzane.")
            return
        
        try:
            song = self.genius.search_song(current_track.title)
            if song and song.lyrics:
                # Split lyrics into chunks for Discord message limit
                lyrics = song.lyrics
                chunks = [lyrics[i:i + 4000] for i in range(0, len(lyrics), 4000)]
                
                for i, chunk in enumerate(chunks):
                    embed = dc.Embed(
                        title=(
                            f"Tekst: {current_track.title}"
                            if i == 0
                            else f"Tekst (część {i + 1})"
                        ),
                        description=chunk,
                        color=dc.Colour.random()
                    )
                    await ctx.send(embed=embed)
            else:
                await ctx.send(f"Nie znaleziono tekstu dla: {current_track.title}")
        except Exception as e:
            Logger.log_error(e, "LYRICS")
            await ctx.send(f"Błąd podczas pobierania tekstu: {e}")
    
    @commands.command(pass_context=False, aliases=["lp", "loop"])
    async def toggle_loop(self, ctx: commands.Context) -> None:
        """Toggle loop mode for current track."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "loop")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        new_status = self.queue_manager.toggle_loop(guild_id)
        
        if new_status:
            await ctx.send("🔄 Zapętlanie włączone - aktualny utwór będzie odtwarzany w pętli.")
        else:
            await ctx.send("▶️ Zapętlanie wyłączone.")
    
    @commands.command(pass_context=True, aliases=["sp", "saveplaylist"])
    async def save_playlist(self, ctx: commands.Context, name: str) -> None:
        """Save current queue as playlist."""
        username, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "saveplaylist")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        queue = self.queue_manager.get_queue(guild_id)
        if not queue:
            await ctx.send("❌ Kolejka jest pusta, nie ma czego zapisać.")
            return
        
        success = PlaylistManager.save_playlist(name, queue, username)
        if success:
            await ctx.send(f"✅ Playlista '{name}' została zapisana z {len(queue)} utworami.")
        else:
            await ctx.send(f"❌ Błąd podczas zapisywania playlisty '{name}'.")
    
    @commands.command(pass_context=True, aliases=["loadp", "loadplaylist"])
    async def load_playlist(self, ctx: commands.Context, name: str) -> None:
        """Load saved playlist."""
        username, guild_id = await UserManager.get_user_info(ctx)
        
        # Check rate limits
        can_proceed, error_msg = self._check_user_limits(ctx, "loadplaylist")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return
        
        playlist_data = PlaylistManager.load_playlist(name)
        if not playlist_data:
            await ctx.send(f"❌ Playlista '{name}' nie istnieje.")
            return
        
        tracks = playlist_data["utwory"]
        if not tracks:
            await ctx.send("❌ Playlista jest pusta.")
            return
        
        # Check user limits
        can_add_all, max_addable = self.rate_limiter.can_add_tracks(
            ctx.author.id, guild_id, len(tracks)
        )
        
        # Update track ownership to current user
        tracks_to_add = tracks[:max_addable] if not can_add_all else tracks
        for track in tracks_to_add:
            track.user = username
        
        # Add tracks to queue
        self.queue_manager.add_tracks(guild_id, tracks_to_add)
        self.rate_limiter.add_tracks_to_user_count(ctx.author.id, guild_id, len(tracks_to_add))
        
        # Send confirmation
        embed = dc.Embed(
            title=f"Wczytano playlistę: {name}",
            description=f"Dodano {len(tracks_to_add)} utworów do kolejki.",
            color=BotConfig.COLORS["success"]
        )
        embed.add_field(name="Utworzona przez", value=playlist_data["utworzony_przez"], inline=True)
        embed.add_field(name="Data utworzenia", value=playlist_data["utworzony_dnia"], inline=True)
        
        if not can_add_all:
            embed.add_field(
                name="Uwaga",
                value=f"Dodano tylko {len(tracks_to_add)} z {len(tracks)} utworów (limit użytkownika)",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        # Start playing if needed
        if ctx.author.voice:
            voice_client = await self._get_voice_client(ctx)
            if voice_client and not voice_client.is_playing():
                await self._play_next_track(ctx)
        else:
            await ctx.send("Dołącz do kanału głosowego, aby rozpocząć odtwarzanie.")
    
    @commands.command(pass_context=False, aliases=["pl", "playlists"])
    async def list_playlists(self, ctx: commands.Context) -> None:
        """List all saved playlists."""
        await UserManager.get_user_info(ctx)
        
        playlists = PlaylistManager.get_playlist_list()
        if not playlists:
            await ctx.send("❌ Nie znaleziono żadnych zapisanych playlist.")
            return
        
        embed = dc.Embed(title="Zapisane playlisty", color=BotConfig.COLORS["info"])
        
        for playlist in playlists:
            embed.add_field(
                name=playlist["name"],
                value=f"Utworów: {playlist['track_count']}\nUtworzył: {playlist['creator']}\nData: {playlist['created_date']}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["autodj", "similar"])
    async def toggle_auto_dj(self, ctx: commands.Context, enabled: bool = None) -> None:
        """Toggle AutoDJ (automatic similar track addition)."""
        _, guild_id = await UserManager.get_user_info(ctx)
        
        if enabled is None:
            # Toggle current state
            self.auto_dj_enabled[guild_id] = not self.auto_dj_enabled.get(guild_id, True)
        else:
            # Set specific state
            self.auto_dj_enabled[guild_id] = enabled
        
        if self.auto_dj_enabled[guild_id]:
            await ctx.send("🎧 AutoDJ włączony - automatycznie dodam podobne utwory, gdy kolejka będzie się kończyć.")
        else:
            await ctx.send("⏹️ AutoDJ wyłączony - nie będę dodawać podobnych utworów.")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Handle command errors with improved logging."""
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Brakujący argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Nieprawidłowy argument: {error}")
        elif isinstance(error, commands.CommandNotFound):
            # Ignore unknown commands
            pass
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ Nie masz uprawnień do używania tej komendy.")
        else:
            await ctx.send(f"❌ Wystąpił błąd: {error}")
            Logger.log_error(error, f"COMMAND_ERROR: {ctx.command}")