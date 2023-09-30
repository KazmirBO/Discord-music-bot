#!/usr/bin/env python3

import discord
import os
import re
import yt_dlp
import random
import datetime
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

command_prefix = "+"
intents = discord.Intents.default()
intents.message_content = True
help_command = None
case_intensive = None

bot = commands.Bot(
    command_prefix=command_prefix,
    intents=intents,
    help_command=help_command,
    case_intensive=case_intensive,
)


man_page = [
    [
        "+man/manual/help/pomoc/h",
        "Wyświetla to okno pomocy",
        False,
    ],
    [
        "+play/graj/odtwórz/p <url>/<tytuł utworu>",
        "Odtwarza utwór z podanego <url> albo dodaje go do kolejki",
        False,
    ],
    [
        "+find/szukaj/przeszukaj/search/f <tytuł utworu>",
        "Zwraca 5 tytułów i linków do podanego <tytuł utworu>",
        False,
    ],
    [
        "+pause/pauza/wstrzymaj/w/ww",
        "Wstrzymuje/Wznawia utwór",
        False,
    ],
    [
        "+skip/pomiń/następny/s/n <numer>",
        "Odtwarza następny utwór/podany <numer> z kolejki",
        False,
    ],
    [
        "+queue/kolejka/q/k",
        "Wyświetla kolejkę odtwarzania",
        False,
    ],
    [
        "+stop/zatrzymaj/z",
        "Zatrzymuje odtwarzanie i czyści kolejkę",
        False,
    ],
    [
        "+disconnect/rozłącz/d",
        "Rozłącza bota z kanału",
        False,
    ],
    [
        "+roll/kości/r <ilość kości> <rodzaj kości>",
        "Wykonuje rzut/y kości",
        False,
    ],
    [
        "+clear/czyść/usuń/c <ilość>",
        "Usuwa ostatnie <ilość> wiadomości",
        False,
    ],
]

Queue = {}

ydl_opts = {
    "format": "bestaudio[ext=webm]/best",
    "outtmpl": "downloads/%(id)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    "before_options": "-nostdin",
    "options": "-vn",
}


def is_youtube_link(text):
    youtube_link_pattern = re.compile(
        r"(https?://)?(www\.)?(youtube|youtu)\.(com|be)/.+$"
    )
    return youtube_link_pattern.match(text) is not None


def is_youtube_playlist_link(text):
    youtube_playlist_pattern = re.compile(
        r"(https?://)?(www\.)?(youtube\.com/playlist\?list=|youtu\.be/)([A-Za-z0-9_-]+)$"
    )
    return youtube_playlist_pattern.match(text) is not None


@bot.event
async def on_ready() -> None:
    print("Bot wystartował!")


@bot.command(aliases=["manual", "help", "pomoc", "h"], pass_context=False)
async def man(ctx) -> None:
    embed = discord.Embed(
        title="Lista komend:",
        color=0x4DFF00,
    )
    embed.set_author(
        name="Manual",
    )
    for iter in man_page:
        embed.add_field(
            name=iter[0],
            value=iter[1],
            inline=iter[2],
        )

    await ctx.send(embed=embed)


@bot.command(pass_context=True, aliases=["graj", "odtwórz", "p"])
async def play(ctx, *, url: str) -> None:
    username = ctx.message.author.display_name
    ident = ctx.message.guild.id
    vs = ctx.author.voice
    await ctx.channel.purge(limit=1)
    if is_youtube_playlist_link(url):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)["entries"]  # type: ignore
        embed = discord.Embed(
            title="Dodano playliste",  # type: ignore
            color=discord.Colour.random(),
        )
        embed.add_field(
            name="Kto dodał",
            value=username,
            inline=False,
        )
        for iter in info:
            embed.add_field(
                name="Uploader",
                value=iter["uploader"],  # type: ignore
                inline=True,
            )
            embed.add_field(
                name="Czas trwania",
                value=str(
                    datetime.timedelta(
                        seconds=int(iter["duration"]),  # type: ignore
                    )
                ),
                inline=True,
            )
            embed.add_field(
                name="URL",
                value=f"https://www.youtube.com/watch?v={iter['id']}",  # type: ignore
                inline=False,
            )
        await ctx.send(embed=embed)
        if vs:
            voice_channel = vs.channel
            if not ctx.voice_client:
                vc = await voice_channel.connect()
            else:
                vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
            for iter in info:
                if ident in Queue:
                    Queue[ident].append(
                        {
                            "url": f"https://www.youtube.com/watch?v={iter['id']}",  # type: ignore
                            "title": iter["title"],  # type: ignore
                            "uploader": iter["uploader"],  # type: ignore
                            "duration": iter["duration"],  # type: ignore
                            "id": iter["id"],  # type: ignore
                            "user": username,
                        }
                    )
                else:
                    Queue[ident] = [
                        {
                            "url": f"https://www.youtube.com/watch?v={iter['id']}",  # type: ignore
                            "title": iter["title"],  # type: ignore
                            "uploader": iter["uploader"],  # type: ignore
                            "duration": iter["duration"],  # type: ignore
                            "id": iter["id"],  # type: ignore
                            "user": username,
                        }
                    ]
            if not vc.is_playing():  # type: ignore
                await play_next(ctx, vc)
        else:
            await ctx.send("Najpierw dołącz do kanału głosowego.")
    else:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if is_youtube_link(url):
                info = ydl.extract_info(url, download=True)
            else:
                info = ydl.extract_info(f"ytsearch:'{url}'", download=True)[  # type: ignore
                    "entries"
                ][
                    0
                ]
        embed = discord.Embed(
            title=f"Dodano: {info['title']}",  # type: ignore
            color=discord.Colour.random(),
        )
        embed.add_field(
            name="Kto dodał",
            value=username,
            inline=True,
        )
        embed.add_field(
            name="Uploader",
            value=info["uploader"],  # type: ignore
            inline=True,
        )
        embed.add_field(
            name="Czas trwania",
            value=str(
                datetime.timedelta(
                    seconds=int(info["duration"]),  # type: ignore
                )
            ),
            inline=True,
        )
        embed.add_field(
            name="URL",
            value=f"https://www.youtube.com/watch?v={info['id']}",  # type: ignore
            inline=False,
        )
        await ctx.send(embed=embed)
        if vs:
            voice_channel = vs.channel
            if not ctx.voice_client:
                vc = await voice_channel.connect()
            else:
                vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
            if ident in Queue:
                Queue[ident].append(
                    {
                        "url": f"https://www.youtube.com/watch?v={info['id']}",  # type: ignore
                        "title": info["title"],  # type: ignore
                        "uploader": info["uploader"],  # type: ignore
                        "duration": info["duration"],  # type: ignore
                        "id": info["id"],  # type: ignore
                        "user": username,
                    }
                )
            else:
                Queue[ident] = [
                    {
                        "url": f"https://www.youtube.com/watch?v={info['id']}",  # type: ignore
                        "title": info["title"],  # type: ignore
                        "uploader": info["uploader"],  # type: ignore
                        "duration": info["duration"],  # type: ignore
                        "id": info["id"],  # type: ignore
                        "user": username,
                    }
                ]
            if not vc.is_playing():  # type: ignore
                await play_next(ctx, vc)
        else:
            await ctx.send("Najpierw dołącz do kanału głosowego.")


@bot.command(
    pass_context=True, aliases=["szukaj", "przeszukaj", "search", "f"]
)
async def find(ctx, *, url: str) -> None:
    await ctx.channel.purge(limit=1)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch5:'{url}'", download=False)
    username = ctx.message.author.display_name
    embed = discord.Embed(
        title="Wybierz link interesującego ciebie utworu:",  # type: ignore
        color=discord.Colour.random(),
    )
    embed.add_field(
        name="Kto dodał",
        value=username,
        inline=True,
    )
    for i in info["entries"]:  # type: ignore
        embed.add_field(
            name=i["title"],
            value=f"https://www.youtube.com/watch?v={i['id']}",
            inline=False,
        )
    await ctx.send(embed=embed)


@tasks.loop(seconds=5.0)
async def music_loop(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not vc.is_playing() and vc:  # type: ignore
        await play_next(ctx, vc)


async def play_next(ctx, vc, pos: int = 0) -> None:
    ident = ctx.message.guild.id
    if Queue[ident] != []:
        info = Queue[ident].pop(pos)
        try:
            vc.play(discord.FFmpegPCMAudio(f"./downloads/{info['id']}.webm"))
            embed = discord.Embed(
                title=f"Teraz odtwarzane: {info['title']}",
                color=discord.Colour.random(),
            )
            embed.add_field(
                name="Kto dodał",
                value=info["user"],
                inline=True,
            )
            embed.add_field(
                name="Uploader",
                value=info["uploader"],
                inline=True,
            )
            embed.add_field(
                name="Czas trwania",
                value=str(
                    datetime.timedelta(
                        seconds=int(info["duration"]),
                    )
                ),
                inline=True,
            )
            embed.add_field(
                name="URL",
                value=f"https://www.youtube.com/watch?v={info['id']}",  # type: ignore
                inline=False,
            )
            await ctx.send(embed=embed)
            music_loop.start(ctx)
        except Exception as err:
            print(f"Wystąpił błąd: {err=}, {type(err)=}")
    else:
        await vc.disconnect()


@bot.command(pass_context=False, aliases=["pauza", "wstrzymaj", "w", "ww"])
async def pause(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None and vc.is_playing():  # type: ignore
        await ctx.send(
            "Utwór został wstrzymany, \
            aby wznowić wpisz ponownie `+pause`."
        )
        vc.pause()  # type: ignore
    elif vc.paused():  # type: ignore
        await ctx.send(
            "Utwór został wstrzymany, \
            aby wznowić wpisz ponownie `+pause`."
        )
        vc.resume()  # type: ignore
    else:
        await ctx.send("Wystąpił błąd! Nie ma czego wstrzymać albo wznowić.")


@bot.command(pass_context=True, aliases=["pomiń", "następny", "s", "n"])
async def skip(ctx, pos: int = 1) -> None:
    ident = ctx.message.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None and len(Queue[ident]) >= pos:
        if vc.is_playing():  # type: ignore
            vc.stop()  # type: ignore
        await play_next(ctx, vc, pos - 1)
    elif len(Queue[ident]) < pos:
        await ctx.send("Kolejka jest pusta.")
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command(pass_context=False, aliases=["kolejka", "q", "k"])
async def queue(ctx) -> None:
    ident = ctx.message.guild.id
    if ident in Queue:
        embed = discord.Embed(
            title="Kolejka odtwarzania:",
            color=discord.Colour.random(),
        )
        for i, info in enumerate(Queue[ident], start=1):
            date = str(datetime.timedelta(seconds=int(info["duration"])))
            embed.add_field(
                name=f"Utwór w kolejce: {i}",
                value="{0}\n{1}\n{2}\n{3}".format(
                    info["title"],
                    info["uploader"],
                    date,
                    f"https://www.youtube.com/watch?v={info['id']}",  # type: ignore
                ),
                inline=False,
            )
        await ctx.send(embed=embed)
    else:
        await ctx.send("Kolejka jest pusta.")


@bot.command(pass_context=False, aliases=["zatrzymaj", "z"])
async def stop(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    ident = ctx.message.guild.id
    if vc is not None and vc.is_playing():  # type: ignore
        vc.stop()  # type: ignore
        Queue[ident].clear()
    else:
        await ctx.send("Nie ma czego zatrzymać.")


@bot.command(pass_context=False, aliases=["rozłącz", "d"])
async def disconnect(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None:
        await vc.disconnect()  # type: ignore
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command(pass_context=True, aliases=["kości", "r"])
async def roll(ctx, ilosc: int, kosc: int) -> None:
    embed = discord.Embed(
        title="Rut kością",
        color=0x4DFF00,
    )
    embed.set_author(
        name="Symulator rzutu kością",
    )
    for i in range(ilosc):
        embed.add_field(
            name=f"Kość: {str(i + 1)}",
            value=random.randint(1, kosc),
        )
    await ctx.send(embed=embed)


@bot.command(pass_context=True, aliases=["czyść", "usuń", "c"])
async def clear(ctx, num: int = 0):
    await ctx.channel.purge(limit=num + 1)


bot.run(TOKEN)  # type: ignore
