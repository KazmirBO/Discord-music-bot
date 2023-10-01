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
        "+pause/resume/wznów/wstrzymaj/w/ww/r",
        "Wstrzymuje utwór",
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
        "+delete/usuń/qd <numer>",
        "Usuwa wybrany <numer> z kolejki odtwarzania",
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
        "+clear/czyść/c <ilość>",
        "Usuwa ostatnie <ilość> wiadomości",
        False,
    ],
]

Queue = {}
Player = {}

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

ydl = yt_dlp.YoutubeDL(ydl_opts)

yt_link = "https://www.youtube.com/watch?v="


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


def track_info(info: list, username: str):
    return {
        "url": f"{yt_link}{info['id']}",  # type: ignore
        "title": info["title"],  # type: ignore
        "uploader": info["uploader"],  # type: ignore
        "duration": info["duration"],  # type: ignore
        "id": info["id"],  # type: ignore
        "user": username,
    }


def get_yt_info(url: str):
    return ydl.extract_info(url, download=True)


async def get_vc(ctx, vs):
    if not ctx.voice_client:
        return vs.channel.connect()
    return discord.utils.get(bot.voice_clients, guild=ctx.guild)


def set_Queue(ident: int, Queue, info, username: str) -> None:
    if ident in Queue:
        Queue[ident].append(
            track_info(
                info=info,  # type: ignore
                username=username,
            )
        )
    else:
        Queue[ident] = [
            track_info(
                info=info,  # type: ignore
                username=username,
            )
        ]


def get_ytsearch_info(url: str, ilosc: str = ""):
    return ydl.extract_info(f"ytsearch{ilosc}:'{url}'", download=True)


def track_embed(text: str, info: list, username: str = ""):
    if not username:
        username = info["user"]  # type: ignore

    embed = discord.Embed(
        title=f"{text}: {info['title']}",  # type: ignore
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
        value=f"{yt_link}{info['id']}",  # type: ignore
        inline=False,
    )
    return embed


def playlist_embed(info: list, username: str = ""):
    if not username:
        username = info["user"]  # type: ignore

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
            value=f"{yt_link}{iter['id']}",  # type: ignore
            inline=False,
        )
    return embed


@bot.event
async def on_ready() -> None:
    print("Bot wystartował!")


@bot.command(aliases=["manual", "help", "pomoc", "h"], pass_context=False)
async def man(ctx) -> None:
    await ctx.channel.purge(limit=1)
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
    await ctx.channel.purge(limit=1)
    if is_youtube_playlist_link(text=url):
        info = get_yt_info(url=url)["entries"]  # type: ignore
        embed = playlist_embed(info=info, username=username)
        await ctx.send(embed=embed)
        if ctx.author.voice:
            vc = await get_vc(ctx=ctx, vs=ctx.author.voice)
            for iter in info:
                set_Queue(
                    ident=ident, Queue=Queue, info=iter, username=username
                )
            if not vc.is_playing():  # type: ignore
                await play_next(ctx=ctx, vc=vc)
        else:
            await ctx.send("Najpierw dołącz do kanału głosowego.")
    else:
        if is_youtube_link(text=url):
            info = get_yt_info(url=url)
        else:
            info = get_ytsearch_info(url=url)["entries"][0]  # type: ignore
        embed = track_embed(
            text="Dodano",
            info=info,  # type: ignore
            username=username,
        )
        await ctx.send(embed=embed)
        if ctx.author.voice:
            vc = await get_vc(ctx=ctx, vs=ctx.author.voice)
            set_Queue(ident=ident, Queue=Queue, info=info, username=username)
            if not vc.is_playing():  # type: ignore
                await play_next(ctx, vc)
        else:
            await ctx.send("Najpierw dołącz do kanału głosowego.")


@bot.command(
    pass_context=True, aliases=["szukaj", "przeszukaj", "search", "f"]
)
async def find(ctx, *, url: str) -> None:
    await ctx.channel.purge(limit=1)
    info = get_ytsearch_info(url=url, ilosc="5")["entries"]  # type: ignore
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
    for i in info:
        embed.add_field(
            name=i["title"],
            value=f"{yt_link}{i['id']}",
            inline=False,
        )
    await ctx.send(embed=embed)


@tasks.loop(seconds=5.0)
async def music_loop(ctx):
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not vc.is_playing() and vc and not vc.is_paused():  # type: ignore
        await play_next(ctx, vc)


async def play_next(ctx, vc, pos: int = 0) -> None:
    ident = ctx.message.guild.id
    if Queue[ident] != []:
        info = Queue[ident].pop(pos)
        try:
            vc.play(discord.FFmpegPCMAudio(f"./downloads/{info['id']}.webm"))
            embed = track_embed(
                text="Teraz odtwarzane",
                info=info,  # type: ignore
            )
            await ctx.send(embed=embed)
            music_loop.start(ctx)
        except Exception as err:
            print(f"Wystąpił błąd: {err=}, {type(err)=}")
    else:
        await vc.disconnect()


@bot.command(
    pass_context=False,
    aliases=["pauza", "resume", "wznów", "wstrzymaj", "w", "ww"],
)
async def pause(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None and vc.is_playing():  # type: ignore
        await ctx.send(
            "Utwór został wstrzymany, aby wznowić wpisz ponownie `+pause`."
        )
        vc.pause()  # type: ignore
    elif vc.is_paused():  # type: ignore
        await ctx.send("Utwór został wznowiony!")
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
    if ident in Queue and Queue[ident] != []:
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
                    f"{yt_link}{info['id']}",  # type: ignore
                ),
                inline=False,
            )
        await ctx.send(embed=embed)
    else:
        await ctx.send("Kolejka jest pusta.")


@bot.command(pass_context=True, aliases=["usuń", "qd"])
async def delete(ctx, pos=None) -> None:
    ident = ctx.message.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if pos is not None and vc is not None and len(Queue[ident]) >= int(pos):
        info = Queue[ident].pop(int(pos) - 1)
        embed = track_embed(
            text="Usunięto z kolejki",
            info=info,  # type: ignore
        )
        await ctx.send(embed=embed)
    elif pos is None:
        await ctx.send("Podaj pozycję do usunięcia!")
    elif len(Queue[ident]) < int(pos) or int(pos) < 0:
        await ctx.send("Wybrałeś zły numer.")
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command(pass_context=False, aliases=["zatrzymaj", "z"])
async def stop(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None and vc.is_playing():  # type: ignore
        vc.stop()  # type: ignore
        Queue[ctx.message.guild.id].clear()
    else:
        await ctx.send("Nie ma czego zatrzymać.")


@bot.command(pass_context=False, aliases=["rozłącz", "d"])
async def disconnect(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None:
        await vc.disconnect()  # type: ignore
        Queue[ctx.message.guild.id].clear()
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command(pass_context=True, aliases=["kości", "rzuć"])
async def roll(ctx, ilosc: int, kosc: int) -> None:
    embed = discord.Embed(
        title="Rut kością",
        color=0x4DFF00,
    )
    embed.set_author(
        name=f"Symulator rzutu kością {ilosc}d{kosc}",
    )
    for i in range(ilosc):
        embed.add_field(
            name=f"Kość: {str(i + 1)}d{kosc}",
            value=random.randint(1, kosc),
        )
    await ctx.send(embed=embed)


@bot.command(pass_context=True, aliases=["czyść", "c"])
async def clear(ctx, num: int = 0):
    await ctx.channel.purge(limit=num + 1)


bot.run(TOKEN)  # type: ignore
