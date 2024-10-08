#!/usr/bin/env python3

import discord as dc
import re
import yt_dlp
import datetime as dt
import shutil
import os
from discord.ext import commands, tasks


class MusicCog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.info = {}
        self.Qu = {}
        self.Pl = {}
        self.Loop = {}
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

    def is_youtube_link(self, text) -> bool:
        link = re.compile(r"(https?://)?(www\.)?(youtube|youtu)\.(com|be)/.+$")
        return link.match(text) is not None

    def is_youtube_playlist_link(self, text) -> bool:
        link = re.compile(
            r"(https?://)?(www\.)?(youtube|youtu)\.(com|be)/playlist\?list=.+$"
        )
        return link.match(text) is not None

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

    def get_yts_info(self, url: str, ilosc: str = ""):
        return self.ydl.extract_info(f"ytsearch{ilosc}:'{url}'")

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

    async def play_next(self, ctx, pos: int = 0) -> None:
        id = ctx.message.guild.id
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
        else:
            self.info[id].clear()
            await self.Pl[id].disconnect()
            if all(not queue for queue in self.Qu.values()) and os.path.exists(
                "./files"
            ):
                shutil.rmtree("./files")

    async def get_user_id(self, ctx) -> tuple:
        await ctx.channel.purge(limit=1)
        return ctx.message.author.display_name, ctx.message.guild.id

    @tasks.loop(seconds=5.0)
    async def music_loop(self, ctx) -> None:
        id = ctx.message.guild.id
        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if self.Pl[id]:
            if not self.Pl[id].is_playing() and not self.Pl[id].is_paused():
                await self.play_next(ctx)

    @commands.command(pass_context=True, aliases=["p", "play"])
    async def _odtworz_muzyke(self, ctx, *, url: str) -> None:
        username, id = await self.get_user_id(ctx=ctx)
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
                date = str(
                    dt.timedelta(
                        seconds=int(self.info[id]["duration"]),
                    )
                )
                embed.add_field(
                    name="Aktualnie odtwarzany:",
                    value="{0}\n{1}\n{2}\n{3}\n{4}".format(
                        self.info[id]["title"],
                        self.info[id]["uploader"],
                        date,
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
        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if pos and self.Pl[id] and len(self.Qu[id]) >= int(pos):
            info = self.Qu[id].pop(int(pos) - 1)
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
        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        self.Pl[id].stop()
        self.Qu[ctx.message.guild.id].clear()

    @commands.command(pass_context=False, aliases=["d", "disconnect"])
    async def _rozlacz(self, ctx) -> None:
        _, id = await self.get_user_id(ctx=ctx)
        self.Pl[id] = dc.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if self.Pl[id] is not None:
            self.info[id].clear()
            await self.Pl[id].disconnect()
            self.Qu[ctx.message.guild.id].clear()
        else:
            await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")
