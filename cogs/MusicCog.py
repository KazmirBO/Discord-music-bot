#!/usr/bin/env python3

import discord as dc
import re
import yt_dlp
import datetime as dt
import shutil
import os
import json
import lyricsgenius
import time
from collections import defaultdict
from discord.ext import commands, tasks


class MusicCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.info = {}
        self.Qu = {}
        self.Pl = {}
        self.Loop = {}
        self.looping = {}

        # 1. Zabezpieczenia przed nadużyciami
        self.user_cooldowns = {}  # Śledzenie czasu ostatniego użycia komend
        self.user_queue_items = defaultdict(
            lambda: defaultdict(int)
        )  # Liczba utworów w kolejce per użytkownik
        self.max_queue_per_user = (
            15  # Maksymalna liczba utworów na użytkownika w kolejce
        )
        # Czas odnowienia (w sekundach) między komendami
        self.cooldown_time = 3

        # 7. Cache'owanie wyników wyszukiwania
        self.search_cache = {}  # Cache dla wyników wyszukiwania
        self.cache_expiry = 3600  # Cache ważny przez 1 godzinę (w sekundach)

        self.ydl_opts = {
            "format": "bestaudio[ext=webm]/best",
            "outtmpl": "files/%(id)s.%(ext)s",
            "download": True,
            "restrictfilenames": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "logtostderr": False,
            "quiet": True,
            "no_warnings": True,
            "default_search": "auto",
            "source_address": "0.0.0.0",
            "verbose": True,
        }
        self.ffmpegopts = {
            "before_options": "-nostdin",
            "options": "-vn",
        }
        self.ydl = yt_dlp.YoutubeDL(self.ydl_opts)
        self.yt_link = "https://www.youtube.com/watch?v="

        # Inicjalizacja API Genius do tekstów piosenek (wymaga tokenu API)
        try:
            self.genius = lyricsgenius.Genius(os.getenv("GENIUS_TOKEN", ""))
        except:
            self.genius = None

        # Uruchom zadanie czyszczenia cache co godzinę
        self.clear_cache.start()

    def is_youtube_link(self, text) -> bool:
        link = re.compile(r"(https?://)?(www\.)?(youtube|youtu)\.(com|be)/.+$")
        return link.match(text) is not None

    def is_youtube_playlist_link(self, text) -> bool:
        link = re.compile(
            r"(https?://)?(www\.)?(youtube|youtu)\.(com|be)/playlist\?list=.+$"
        )
        return link.match(text) is not None

    # 1. Sprawdzanie limitów i cooldownów użytkownika
    def check_user_limits(self, user_id, guild_id, command_type="play"):
        current_time = time.time()

        # Sprawdź cooldown komendy
        cooldown_key = f"{user_id}:{guild_id}:{command_type}"
        if cooldown_key in self.user_cooldowns:
            last_use = self.user_cooldowns[cooldown_key]
            if current_time - last_use < self.cooldown_time:
                return (
                    False,
                    f"Spokojnie! Poczekaj {
                        self.cooldown_time} sekund między komendami.",
                )

        # Aktualizuj czas ostatniego użycia
        self.user_cooldowns[cooldown_key] = current_time

        # Sprawdź limit kolejki dla komend odtwarzania
        if command_type == "play":
            current_count = self.user_queue_items[guild_id][user_id]
            if current_count >= self.max_queue_per_user:
                return (
                    False,
                    f"Osiągnąłeś limit {
                        self.max_queue_per_user} utworów w kolejce. Poczekaj, aż niektóre zostaną odtworzone.",
                )

        return True, ""

    def track_info(self, info: list, username: str) -> dict:
        return {
            "url": f"{self.yt_link}{info['id']}",  # type: ignore
            "title": info["title"],  # type: ignore
            "uploader": info["uploader"],  # type: ignore
            "duration": info["duration"],  # type: ignore
            "id": info["id"],  # type: ignore
            "user": username,
        }

    async def get_vc(self, ctx, vs):
        if not ctx.voice_client:
            return await vs.channel.connect()
        return dc.utils.get(self.bot.voice_clients, guild=ctx.guild)

    def set_queue(self, id: int, info, username: str) -> None:
        if id in self.Qu:
            self.Qu[id].append(self.track_info(info=info, username=username))
        else:
            self.Qu[id] = [self.track_info(info=info, username=username)]

        # 1. Aktualizuj licznik utworów użytkownika
        user_id = self.get_user_id_from_name(username, id)
        if user_id:
            self.user_queue_items[id][user_id] += 1

    # Pomocnicza metoda do uzyskania ID użytkownika na podstawie nazwy
    def get_user_id_from_name(self, username, guild_id):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None

        for member in guild.members:
            if member.display_name == username:
                return member.id

        return None

    # 7. Funkcja do sprawdzania i zapisu do cache'u
    def get_yts_info(self, url: str, ilosc: str = ""):
        cache_key = f"{url}:{ilosc}"

        # Sprawdź, czy wynik jest w cache'u i czy nie wygasł
        if cache_key in self.search_cache:
            cache_time, cache_data = self.search_cache[cache_key]
            if time.time() - cache_time < self.cache_expiry:
                return cache_data

        # Jeśli nie ma w cache lub wygasł, wykonaj wyszukiwanie
        result = self.ydl.extract_info(f"ytsearch{ilosc}:'{url}'")

        # Zapisz wynik do cache'u
        self.search_cache[cache_key] = (time.time(), result)

        return result

    # Zadanie czyszczenia wygasłych elementów cache'u
    @tasks.loop(hours=1)
    async def clear_cache(self):
        current_time = time.time()
        expired_keys = []

        for key, (cache_time, _) in self.search_cache.items():
            if current_time - cache_time > self.cache_expiry:
                expired_keys.append(key)

        for key in expired_keys:
            del self.search_cache[key]

        print(f"Wyczyszczono {len(expired_keys)} wygasłych elementów cache'u.")

    def track_embed(self, text: str, info: list, username: str = ""):
        if not username:
            username = info["user"]  # type: ignore

        embed = dc.Embed(
            title=f"{text}: {info['title']}",  # type: ignore
            color=dc.Colour.random(),
        )
        embed.add_field(name="Kto dodał", value=username, inline=True)
        embed.add_field(
            name="Uploader",
            value=info["uploader"],  # type: ignore
            inline=True,
        )
        embed.add_field(
            name="Czas trwania",
            value=str(
                dt.timedelta(
                    seconds=int(info["duration"]),  # type: ignore
                )
            ),
            inline=True,
        )
        embed.add_field(
            name="URL",
            value=f"{self.yt_link}{info['id']}",  # type: ignore
            inline=False,
        )
        return embed

    def playlist_embed(self, info: list, username: str = ""):
        if not username:
            username = info["user"]  # type: ignore

        embed = dc.Embed(title="Dodano", color=dc.Colour.random())
        embed.add_field(name="Kto dodał", value=username, inline=False)
        for iter in info:
            embed.add_field(
                name="Uploader",
                value=iter["uploader"],
                inline=True,
            )
            embed.add_field(
                name="Czas trwania",
                value=str(
                    dt.timedelta(
                        seconds=int(iter["duration"]),
                    )
                ),
                inline=True,
            )
            embed.add_field(
                name="URL",
                value=f"{self.yt_link}{iter['id']}",
                inline=False,
            )
        return embed

    def get_progress_bar(self, current, total, length=15):
        """Tworzy pasek postępu dla aktualnie odtwarzanego utworu."""
        filled = int(length * current / total)
        bar = "▓" * filled + "░" * (length - filled)
        percent = int(100 * current / total)
        return f"{bar} {percent}%"

    def cleanup_files(self, file_id=None):
        """Usuwa pojedynczy plik lub wszystkie niepotrzebne pliki."""
        if file_id:
            try:
                if os.path.exists(f"./files/{file_id}.webm"):
                    os.remove(f"./files/{file_id}.webm")
            except Exception as e:
                print(f"Błąd podczas usuwania pliku: {e}")
        else:
            if not os.path.exists("./files"):
                return

            # Zbierz wszystkie używane ID
            active_ids = set()
            for server_id in self.Qu:
                for track in self.Qu[server_id]:
                    active_ids.add(track["id"])

            for server_id in self.info:
                if self.info[server_id]:
                    active_ids.add(self.info[server_id]["id"])

            # Usuń nieużywane pliki
            for file in os.listdir("./files"):
                if file.endswith(".webm"):
                    file_id = file.split(".")[0]
                    if file_id not in active_ids:
                        try:
                            os.remove(f"./files/{file}")
                        except Exception as e:
                            print(f"Błąd podczas usuwania pliku: {e}")

    # 6. Funkcja pobierająca podobne utwory
    async def get_similar_tracks(self, ctx, track_info):
        """Pobiera utwory podobne do aktualnie odtwarzanego."""
        if not track_info:
            return []

        # Użyj tytułu i nazwy kanału jako podstawy do wyszukiwania
        query = f"{track_info['title']} {track_info['uploader']} podobne"

        try:
            # Pobierz 3 podobne utwory
            search_results = self.get_yts_info(url=query, ilosc="3")
            similar_tracks = []

            # Upewnij się, że nie dodajemy ponownie tego samego utworu
            current_id = track_info["id"]

            for track in search_results["entries"]:
                if track["id"] != current_id:
                    similar_tracks.append(track)

            return similar_tracks
        except Exception as e:
            print(f"Błąd podczas pobierania podobnych utworów: {e}")
            return []

    # 6. Dodaj podobne utwory do kolejki
    async def add_similar_tracks(self, ctx, track_info):
        """Dodaje podobne utwory do kolejki, gdy jest prawie pusta."""
        id = ctx.message.guild.id

        # Sprawdź, czy kolejka jest prawie pusta (mniej niż 2 utwory)
        if id in self.Qu and len(self.Qu[id]) < 2:
            similar_tracks = await self.get_similar_tracks(ctx, track_info)

            if similar_tracks:
                await ctx.send("🎵 Dodaję podobne utwory do kolejki...")

                for track in similar_tracks:
                    self.set_queue(id=id, info=track, username="AutoDJ 🤖")

                embed = dc.Embed(
                    title="Dodano podobne utwory",
                    description=f"Dodano {
                        len(similar_tracks)} podobnych utworów do kolejki.",
                    color=dc.Colour.purple(),
                )
                await ctx.send(embed=embed)

    async def play_next(self, ctx, pos: int = 0) -> None:
        id = ctx.message.guild.id
        # Zapisz poprzednie ID do czyszczenia
        old_id = self.info[id]["id"] if id in self.info and self.info[id] else None

        # Aktualizuj licznik utworów użytkownika po odtworzeniu
        if old_id and id in self.info and "user" in self.info[id]:
            user_id = self.get_user_id_from_name(self.info[id]["user"], id)
            if (
                user_id
                and id in self.user_queue_items
                and user_id in self.user_queue_items[id]
            ):
                self.user_queue_items[id][user_id] = max(
                    0, self.user_queue_items[id][user_id] - 1
                )

        if self.Qu[id]:
            self.info[id] = self.Qu[id].pop(pos)
            self.Pl[id].play(
                dc.FFmpegPCMAudio(f"./files/{self.info[id]['id']}.webm"),
            )
            embed = self.track_embed(
                text="Teraz odtwarzane",
                info=self.info[id],
            )
            await ctx.send(embed=embed)
            self.Loop[id] = self.music_loop
            if self.Loop[id].is_running():
                self.Loop[id].restart(ctx)
            else:
                self.Loop[id].start(ctx)

            # Wyczyść poprzedni plik
            if old_id:
                self.cleanup_files(old_id)

            # 6. Sprawdź, czy kolejka jest prawie pusta i dodaj podobne utwory
            await self.add_similar_tracks(ctx, self.info[id])
        else:
            self.info[id].clear()
            await self.Pl[id].disconnect()

            # Uruchom czyszczenie plików
            self.cleanup_files()

    async def get_user_id(self, ctx) -> tuple:
        await ctx.channel.purge(limit=1)
        return ctx.message.author.display_name, ctx.message.guild.id

    @tasks.loop(seconds=5.0)
    async def music_loop(self, ctx) -> None:
        id = ctx.message.guild.id
        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if self.Pl[id]:
            if not self.Pl[id].is_playing() and not self.Pl[id].is_paused():
                # Jeśli zapętlanie jest włączone, dodaj aktualny utwór z powrotem do kolejki
                if id in self.looping and self.looping[id] and self.info[id]:
                    self.Qu[id].insert(0, self.info[id].copy())
                await self.play_next(ctx)

    @commands.command(pass_context=True, aliases=["p", "play"])
    async def _odtworz_muzyke(self, ctx, *, url: str) -> None:
        username, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "play")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        if self.is_youtube_playlist_link(text=url):
            info = self.ydl.extract_info(url)["entries"]  # type: ignore
            playlist = True
        else:
            if self.is_youtube_link(text=url):
                info = self.ydl.extract_info(url)
            else:
                info = self.get_yts_info(url=url)["entries"][0]  # type: ignore
            playlist = False
        if info:
            if playlist:
                embed = self.playlist_embed(
                    info=info,  # type: ignore
                    username=username,
                )
            else:
                embed = self.track_embed(
                    text="Dodano",
                    info=info,  # type: ignore
                    username=username,
                )
            await ctx.send(embed=embed)
            if ctx.author.voice:
                self.Pl[id] = await self.get_vc(
                    ctx=ctx,
                    vs=ctx.author.voice,
                )
                if playlist:
                    # Sprawdź, czy użytkownik nie przekroczy limitu dodając playlistę
                    total_tracks = len(info)
                    current_tracks = self.user_queue_items[id][ctx.author.id]
                    if current_tracks + total_tracks > self.max_queue_per_user:
                        await ctx.send(
                            f"⚠️ Ta playlista ma {total_tracks} utworów, co przekroczy twój limit {
                                self.max_queue_per_user}. Dodano tylko pierwsze {self.max_queue_per_user - current_tracks}."
                        )
                        # Dodaj tylko tyle utworów, ile możliwe w limicie
                        for i, iter in enumerate(info):
                            if i < (self.max_queue_per_user - current_tracks):
                                self.set_queue(
                                    id=id,
                                    info=iter,
                                    username=username,
                                )
                            else:
                                break
                    else:
                        for iter in info:
                            self.set_queue(
                                id=id,
                                info=iter,
                                username=username,
                            )
                else:
                    self.set_queue(
                        id=id,
                        info=info,
                        username=username,
                    )
                if not self.Pl[id].is_playing():
                    await self.play_next(ctx=ctx)
            else:
                await ctx.send("Najpierw dołącz do kanału głosowego.")

    @commands.command(pass_context=True, aliases=["f", "find"])
    async def _szukaj(self, ctx, *, url: str) -> None:
        username, _ = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, ctx.guild.id, "find"
        )
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        info = self.get_yts_info(url=url, ilosc="5")["entries"]  # type: ignore
        embed = dc.Embed(
            title="Wybierz link interesującego ciebie utworu:",
            color=dc.Colour.random(),
        )
        embed.add_field(name="Kto dodał", value=username, inline=True)
        for i in info:
            date = str(dt.timedelta(seconds=int(i["duration"])))
            embed.add_field(
                name=f"{i['title']}: {date}",
                value=f"{self.yt_link}{i['id']}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(pass_context=False, aliases=["pr", "pause", "resume"])
    async def _zarzadzaj_odtwarzaniem(self, ctx) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "pause")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if self.Pl[id] is not None and self.Pl[id].is_playing():
            await ctx.send("Utwór został wstrzymany.")
            self.Pl[id].pause()
        elif self.Pl[id].is_paused():
            await ctx.send("Utwór został wznowiony!")
            self.Pl[id].resume()
        else:
            await ctx.send("Wystąpił błąd! Nie ma czego wstrzymać/wznowić.")

    @commands.command(pass_context=True, aliases=["sk", "skip"])
    async def _pomin(self, ctx, pos: int = 1) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "skip")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if self.Pl[id] is not None and len(self.Qu[id]) >= pos:
            if self.Pl[id].is_playing():
                self.Pl[id].stop()
            await self.play_next(ctx, pos - 1)
        elif len(self.Qu[id]) < pos:
            await ctx.send("Kolejka jest pusta.")
        else:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")

    @commands.command(pass_context=False, aliases=["q", "queue"])
    async def _kolejka(self, ctx) -> None:
        _, id = await self.get_user_id(ctx=ctx)
        if id in self.Qu and (self.Qu[id] or self.info[id]):
            embed = dc.Embed(
                title="Kolejka odtwarzania:",
                color=dc.Colour.random(),
            )
            if self.info[id]:
                total_seconds = int(self.info[id]["duration"])
                # Oblicz, ile sekund już odtworzono
                if self.Pl[id] and hasattr(self.Pl[id], "source"):
                    elapsed = getattr(self.Pl[id], "elapsed", 0)
                else:
                    elapsed = 0

                progress_bar = self.get_progress_bar(elapsed, total_seconds)
                elapsed_str = str(dt.timedelta(seconds=int(elapsed)))
                total_str = str(dt.timedelta(seconds=total_seconds))

                embed.add_field(
                    name="Aktualnie odtwarzany:",
                    value="{0}\n{1}\n{2} {3}/{4}\n{5}\n{6}".format(
                        self.info[id]["title"],
                        self.info[id]["uploader"],
                        progress_bar,
                        elapsed_str,
                        total_str,
                        self.info[id]["user"],
                        f"{self.yt_link}{self.info[id]['id']}",
                    ),
                    inline=False,
                )

            if self.Qu[id]:
                for i, info in enumerate(self.Qu[id], start=1):
                    date = str(dt.timedelta(seconds=int(info["duration"])))
                    embed.add_field(
                        name=f"Utwór w kolejce: {i}",
                        value="{0}\n{1}\n{2}\n{3}\n{4}".format(
                            info["title"],
                            info["uploader"],
                            date,
                            info["user"],
                            f"{self.yt_link}{info['id']}",
                        ),
                        inline=False,
                    )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Kolejka jest pusta.")

    @commands.command(pass_context=True, aliases=["dl", "delete"])
    async def _usun(self, ctx, pos=None) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "delete")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if pos and self.Pl[id] and len(self.Qu[id]) >= int(pos):
            # Sprawdź, czy użytkownik usuwa własny utwór lub ma uprawnienia administratora
            track_to_delete = self.Qu[id][int(pos) - 1]
            is_admin = ctx.author.guild_permissions.administrator
            is_owner = track_to_delete["user"] == ctx.author.display_name

            if not (is_admin or is_owner):
                await ctx.send("⚠️ Możesz usuwać tylko swoje utwory z kolejki!")
                return

            info = self.Qu[id].pop(int(pos) - 1)

            # Aktualizuj licznik utworów użytkownika
            user_id = self.get_user_id_from_name(info["user"], id)
            if (
                user_id
                and id in self.user_queue_items
                and user_id in self.user_queue_items[id]
            ):
                self.user_queue_items[id][user_id] = max(
                    0, self.user_queue_items[id][user_id] - 1
                )

            embed = self.track_embed(
                text="Usunięto z kolejki",
                info=info,
            )
            await ctx.send(embed=embed)
        elif pos is None:
            await ctx.send("Podaj pozycję do usunięcia!")
        elif len(self.Qu[id]) < int(pos) or int(pos) < 0:
            await ctx.send("Wybrałeś zły numer.")
        else:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")

    @commands.command(pass_context=False, aliases=["s", "stop"])
    async def _zatrzymaj(self, ctx) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "stop")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        self.Pl[id].stop()
        self.Qu[ctx.message.guild.id].clear()

        # Zresetuj liczniki utworów użytkowników
        if id in self.user_queue_items:
            self.user_queue_items[id].clear()

    @commands.command(pass_context=False, aliases=["d", "disconnect"])
    async def _rozlacz(self, ctx) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "disconnect")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if self.Pl[id] is not None:
            self.info[id].clear()
            await self.Pl[id].disconnect()
            self.Qu[ctx.message.guild.id].clear()

            # Zresetuj liczniki utworów użytkowników
            if id in self.user_queue_items:
                self.user_queue_items[id].clear()
        else:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")

    @commands.command(pass_context=True, aliases=["v", "volume"])
    async def _glosnosc(self, ctx, volume: int = None) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "volume")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if volume is None:
            current_volume = getattr(self.Pl[id], "volume", 100) * 100
            await ctx.send(f"Aktualna głośność: {int(current_volume)}%")
            return

        if volume < 0 or volume > 200:
            await ctx.send("Głośność musi być między 0 a 200%")
            return

        if self.Pl[id] is not None:
            self.Pl[id].volume = volume / 100
            await ctx.send(f"Głośność ustawiona na {volume}%")
        else:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")

    @commands.command(pass_context=True, aliases=["l", "lyrics"])
    async def _tekst(self, ctx) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "lyrics")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        if not self.genius:
            await ctx.send(
                "❌ Funkcja tekstów jest niedostępna - brak tokenu API Genius."
            )
            return

        if id in self.info and self.info[id]:
            title = self.info[id]["title"]
            try:
                song = self.genius.search_song(title)
                if song:
                    lyrics = song.lyrics
                    # Podziel tekst na części o długości max 4000 znaków
                    chunks = [lyrics[i: i + 4000]
                              for i in range(0, len(lyrics), 4000)]

                    for i, chunk in enumerate(chunks):
                        embed = dc.Embed(
                            title=(
                                f"Tekst: {title}"
                                if i == 0
                                else f"Tekst (część {i + 1})"
                            ),
                            description=chunk,
                            color=dc.Colour.random(),
                        )
                        await ctx.send(embed=embed)
                else:
                    await ctx.send(f"Nie znaleziono tekstu dla: {title}")
            except Exception as e:
                await ctx.send(f"Błąd podczas pobierania tekstu: {e}")
        else:
            await ctx.send("Obecnie nic nie jest odtwarzane.")

    @commands.command(pass_context=False, aliases=["lp", "loop"])
    async def _zapetl(self, ctx) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "loop")
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        if id not in self.looping:
            self.looping[id] = False

        self.looping[id] = not self.looping[id]

        if self.looping[id]:
            await ctx.send(
                "🔄 Zapętlanie włączone - aktualny utwór będzie odtwarzany w pętli."
            )
        else:
            await ctx.send("▶️ Zapętlanie wyłączone.")

    @commands.command(pass_context=True, aliases=["sp", "saveplaylist"])
    async def _zapisz_playliste(self, ctx, nazwa: str) -> None:
        username, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "saveplaylist"
        )
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        if id in self.Qu and self.Qu[id]:
            # Utwórz katalog jeśli nie istnieje
            if not os.path.exists("./playlists"):
                os.makedirs("./playlists")

            playlist_data = {
                "nazwa": nazwa,
                "utworzony_przez": username,
                "utworzony_dnia": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "utwory": self.Qu[id],
            }

            with open(f"./playlists/{nazwa}.json", "w", encoding="utf-8") as f:
                json.dump(playlist_data, f, ensure_ascii=False, indent=4)

            await ctx.send(
                f"✅ Playlista '{nazwa}' została zapisana z {
                    len(self.Qu[id])} utworami."
            )
        else:
            await ctx.send("❌ Kolejka jest pusta, nie ma czego zapisać.")

    @commands.command(pass_context=True, aliases=["loadp", "loadplaylist"])
    async def _wczytaj_playliste(self, ctx, nazwa: str) -> None:
        username, id = await self.get_user_id(ctx=ctx)

        # 1. Sprawdzenie limitów użytkownika
        can_proceed, error_msg = self.check_user_limits(
            ctx.author.id, id, "loadplaylist"
        )
        if not can_proceed:
            await ctx.send(f"⚠️ {error_msg}")
            return

        playlist_path = f"./playlists/{nazwa}.json"
        if not os.path.exists(playlist_path):
            await ctx.send(f"❌ Playlista '{nazwa}' nie istnieje.")
            return

        with open(playlist_path, "r", encoding="utf-8") as f:
            playlist_data = json.load(f)

        utwory = playlist_data["utwory"]

        if utwory:
            if id not in self.Qu:
                self.Qu[id] = []

            # Sprawdź, czy użytkownik nie przekroczy limitu dodając playlistę
            total_tracks = len(utwory)
            current_tracks = self.user_queue_items[id][ctx.author.id]

            if current_tracks + total_tracks > self.max_queue_per_user:
                await ctx.send(
                    f"⚠️ Ta playlista ma {total_tracks} utworów, co przekroczy twój limit {
                        self.max_queue_per_user}. Dodano tylko pierwsze {self.max_queue_per_user - current_tracks}."
                )
                # Dodaj tylko tyle utworów, ile możliwe w limicie
                for i, utwór in enumerate(utwory):
                    if i < (self.max_queue_per_user - current_tracks):
                        utwór["user"] = (
                            username  # Zaktualizuj użytkownika do aktualnego
                        )
                        self.Qu[id].append(utwór)
                        self.user_queue_items[id][ctx.author.id] += 1
                    else:
                        break
            else:
                for utwór in utwory:
                    # Zaktualizuj użytkownika do aktualnego
                    utwór["user"] = username
                    self.Qu[id].append(utwór)
                    self.user_queue_items[id][ctx.author.id] += 1

            embed = dc.Embed(
                title=f"Wczytano playlistę: {nazwa}",
                description=f"Dodano {
                    min(total_tracks, self.max_queue_per_user - current_tracks)} utworów do kolejki.",
                color=dc.Colour.green(),
            )
            embed.add_field(
                name="Utworzona przez",
                value=playlist_data["utworzony_przez"],
                inline=True,
            )
            embed.add_field(
                name="Data utworzenia",
                value=playlist_data["utworzony_dnia"],
                inline=True,
            )

            await ctx.send(embed=embed)

            if ctx.author.voice:
                self.Pl[id] = await self.get_vc(ctx=ctx, vs=ctx.author.voice)
                if not self.Pl[id].is_playing():
                    await self.play_next(ctx=ctx)
            else:
                await ctx.send("Dołącz do kanału głosowego, aby rozpocząć odtwarzanie.")
        else:
            await ctx.send("❌ Playlista jest pusta.")

    @commands.command(pass_context=False, aliases=["pl", "playlists"])
    async def _playlisty(self, ctx) -> None:
        await self.get_user_id(ctx=ctx)

        if not os.path.exists("./playlists"):
            await ctx.send("❌ Nie znaleziono żadnych zapisanych playlist.")
            return

        playlists = [f for f in os.listdir(
            "./playlists") if f.endswith(".json")]

        if not playlists:
            await ctx.send("❌ Nie znaleziono żadnych zapisanych playlist.")
            return

        embed = dc.Embed(title="Zapisane playlisty", color=dc.Colour.blue())

        for playlist in playlists:
            nazwa = playlist.replace(".json", "")
            with open(f"./playlists/{playlist}", "r", encoding="utf-8") as f:
                data = json.load(f)

            embed.add_field(
                name=nazwa,
                value=f"Utworów: {len(data['utwory'])}\nUtworzył: {
                    data['utworzony_przez']}\nData: {data['utworzony_dnia']}",
                inline=False,
            )

        await ctx.send(embed=embed)

    # 6. Komenda do włączania/wyłączania automatycznego dobierania podobnych utworów
    @commands.command(aliases=["autodj", "similar"])
    async def _autoodtwarzanie(self, ctx, enabled: bool = None) -> None:
        _, id = await self.get_user_id(ctx=ctx)

        if not hasattr(self, "auto_dj_enabled"):
            self.auto_dj_enabled = {}

        if enabled is None:
            # Przełącz stan
            self.auto_dj_enabled[id] = not self.auto_dj_enabled.get(id, True)
        else:
            # Ustaw określony stan
            self.auto_dj_enabled[id] = enabled

        if self.auto_dj_enabled[id]:
            await ctx.send(
                "🎧 AutoDJ włączony - automatycznie dodam podobne utwory, gdy kolejka będzie się kończyć."
            )
        else:
            await ctx.send("⏹️ AutoDJ wyłączony - nie będę dodawać podobnych utworów.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Brakujący argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Nieprawidłowy argument: {error}")
        elif isinstance(error, commands.CommandNotFound):
            # Ignoruj nieznane komendy
            pass
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ Nie masz uprawnień do używania tej komendy.")
        else:
            await ctx.send(f"❌ Wystąpił błąd: {error}")

            # Log błędów do pliku
            if not os.path.exists("./logs"):
                os.makedirs("./logs")

            with open("./logs/errors.log", "a", encoding="utf-8") as f:
                f.write(f"{dt.datetime.now()}: {error}\n")
