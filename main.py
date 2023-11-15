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
        "+h/help/man",
        "Wyświetla to okno pomocy",
        False,
    ],
    [
        "+p/play <url>/<tytuł utworu>",
        "Odtwarza utwór z podanego <url> albo dodaje go do kolejki",
        False,
    ],
    [
        "+f/find <tytuł utworu>",
        "Zwraca 5 tytułów i linków do podanego <tytuł utworu>",
        False,
    ],
    [
        "+pr/pause/resume",
        "Wstrzymuje utwór",
        False,
    ],
    [
        "+sk/skip <numer>",
        "Odtwarza następny utwór/podany <numer> z kolejki",
        False,
    ],
    [
        "+q/queue",
        "Wyświetla kolejkę odtwarzania",
        False,
    ],
    [
        "+dl/delete <numer>",
        "Usuwa wybrany <numer> z kolejki odtwarzania",
        False,
    ],
    [
        "+s/stop",
        "Zatrzymuje odtwarzanie i czyści kolejkę",
        False,
    ],
    [
        "+d/disconnect",
        "Rozłącza bota z kanału",
        False,
    ],
    [
        "+r/roll <ilość kości> <rodzaj kości>",
        "Wykonuje rzut/y kości",
        False,
    ],
    [
        "+c/clear <ilość>",
        "Usuwa ostatnie <ilość> wiadomości",
        False,
    ],
]

Qu = {}
Pl = {}
ydl_opts = {
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
        r"(https?://)?(www\.)?(youtube|youtu)\.(com|be)/playlist\?list=.+$"
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
    return ydl.extract_info(url)


async def get_vc(ctx, vs):
    if not ctx.voice_client:
        return await vs.channel.connect()
    return discord.utils.get(bot.voice_clients, guild=ctx.guild)


def set_queue(id: int, Qu, info, username: str) -> None:
    if id in Qu:
        Qu[id].append(
            track_info(
                info=info,
                username=username,
            )
        )
    else:
        Qu[id] = [
            track_info(
                info=info,
                username=username,
            )
        ]


def get_ytsearch_info(url: str, ilosc: str = ""):
    return ydl.extract_info(f"ytsearch{ilosc}:'{url}'")


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
        title="Dodano",
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
            value=iter["uploader"],
            inline=True,
        )
        embed.add_field(
            name="Czas trwania",
            value=str(
                datetime.timedelta(
                    seconds=int(iter["duration"]),
                )
            ),
            inline=True,
        )
        embed.add_field(
            name="URL",
            value=f"{yt_link}{iter['id']}",
            inline=False,
        )
    return embed


async def play_next(ctx, pos: int = 0) -> None:
    id = ctx.message.guild.id
    if Qu[id] != []:
        info = Qu[id].pop(pos)
        Pl[id].play(discord.FFmpegPCMAudio(f"./files/{info['id']}.webm"))
        embed = track_embed(
            text="Teraz odtwarzane",
            info=info,
        )
        await ctx.send(embed=embed)
        if not music_loop.is_running():
            music_loop.start(ctx)
    else:
        await Pl[id].disconnect()


@bot.event
async def on_ready() -> None:
    print("Bot wystartował!")


@bot.event
async def on_voice_state_update(member, before, after):
    del after, before
    voice_state = member.guild.voice_client
    if voice_state is not None and len(voice_state.channel.members) == 1:
        await voice_state.disconnect()


@tasks.loop(seconds=5.0)
async def music_loop(ctx) -> None:
    id = ctx.message.guild.id
    Pl[id] = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if Pl[id] and not Pl[id].is_playing() and not Pl[id].is_paused():
        await play_next(ctx)


@bot.command(aliases=["h", "help", "man"], pass_context=False)
async def _pomoc(ctx) -> None:
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


@bot.command(pass_context=True, aliases=["p", "play"])
async def _graj(ctx, *, url: str) -> None:
    await ctx.channel.purge(limit=1)
    username = ctx.message.author.display_name
    id = ctx.message.guild.id
    if is_youtube_playlist_link(text=url):
        info = get_yt_info(url=url)["entries"]  # type: ignore
        playlist = True
    else:
        if is_youtube_link(text=url):
            info = get_yt_info(url=url)
        else:
            info = get_ytsearch_info(url=url)["entries"][0]  # type: ignore
        playlist = False
    if info:
        if playlist:
            embed = playlist_embed(
                info=info,  # type: ignore
                username=username,
            )
        else:
            embed = track_embed(
                text="Dodano",
                info=info,  # type: ignore
                username=username,
            )
        await ctx.send(embed=embed)
        if ctx.author.voice:
            Pl[id] = await get_vc(ctx=ctx, vs=ctx.author.voice)
            if playlist:
                for iter in info:
                    set_queue(
                        id=id,
                        Qu=Qu,
                        info=iter,
                        username=username,
                    )
            else:
                set_queue(id=id, Qu=Qu, info=info, username=username)
            if not Pl[id].is_playing():
                await play_next(ctx=ctx)
        else:
            await ctx.send("Najpierw dołącz do kanału głosowego.")


@bot.command(pass_context=True, aliases=["f", "find"])
async def _szukaj(ctx, *, url: str) -> None:
    await ctx.channel.purge(limit=1)
    info = get_ytsearch_info(url=url, ilosc="5")["entries"]  # type: ignore
    username = ctx.message.author.display_name
    embed = discord.Embed(
        title="Wybierz link interesującego ciebie utworu:",
        color=discord.Colour.random(),
    )
    embed.add_field(
        name="Kto dodał",
        value=username,
        inline=True,
    )
    for i in info:
        date = str(datetime.timedelta(seconds=int(i["duration"])))
        embed.add_field(
            name=f"{i['title']}: {date}",
            value=f"{yt_link}{i['id']}",
            inline=False,
        )
    await ctx.send(embed=embed)


@bot.command(pass_context=False, aliases=["pr", "pause", "resume"])
async def _pauza(ctx) -> None:
    await ctx.channel.purge(limit=1)
    id = ctx.message.guild.id
    Pl[id] = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if Pl[id] is not None and Pl[id].is_playing():
        await ctx.send("Utwór został wstrzymany.")
        Pl[id].pause()
    elif Pl[id].is_paused():
        await ctx.send("Utwór został wznowiony!")
        Pl[id].resume()
    else:
        await ctx.send("Wystąpił błąd! Nie ma czego wstrzymać albo wznowić.")


@bot.command(pass_context=True, aliases=["sk", "skip"])
async def _pomin(ctx, pos: int = 1) -> None:
    await ctx.channel.purge(limit=1)
    id = ctx.message.guild.id
    Pl[id] = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if Pl[id] is not None and len(Qu[id]) >= pos:
        if Pl[id].is_playing():
            Pl[id].stop()
        await play_next(ctx, pos - 1)
    elif len(Qu[id]) < pos:
        await ctx.send("Kolejka jest pusta.")
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command(pass_context=False, aliases=["q", "queue"])
async def _kolejka(ctx) -> None:
    await ctx.channel.purge(limit=1)
    id = ctx.message.guild.id
    if id in Qu and Qu[id] != []:
        embed = discord.Embed(
            title="Kolejka odtwarzania:",
            color=discord.Colour.random(),
        )
        for i, info in enumerate(Qu[id], start=1):
            date = str(datetime.timedelta(seconds=int(info["duration"])))
            embed.add_field(
                name=f"Utwór w kolejce: {i}",
                value="{0}\n{1}\n{2}\n{3}".format(
                    info["title"],
                    info["uploader"],
                    date,
                    f"{yt_link}{info['id']}",
                ),
                inline=False,
            )
        await ctx.send(embed=embed)
    else:
        await ctx.send("Kolejka jest pusta.")


@bot.command(pass_context=True, aliases=["dl", "delete"])
async def _usun(ctx, pos=None) -> None:
    await ctx.channel.purge(limit=1)
    id = ctx.message.guild.id
    Pl[id] = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if pos is not None and Pl[id] is not None and len(Qu[id]) >= int(pos):
        info = Qu[id].pop(int(pos) - 1)
        embed = track_embed(
            text="Usunięto z kolejki",
            info=info,
        )
        await ctx.send(embed=embed)
    elif pos is None:
        await ctx.send("Podaj pozycję do usunięcia!")
    elif len(Qu[id]) < int(pos) or int(pos) < 0:
        await ctx.send("Wybrałeś zły numer.")
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command(pass_context=False, aliases=["s", "stop"])
async def _zatrzymaj(ctx) -> None:
    await ctx.channel.purge(limit=1)
    id = ctx.message.guild.id
    Pl[id] = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    Pl[id].stop()
    Qu[ctx.message.guild.id].clear()


@bot.command(pass_context=False, aliases=["d", "disconnect"])
async def _rozlacz(ctx) -> None:
    await ctx.channel.purge(limit=1)
    id = ctx.message.guild.id
    Pl[id] = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if Pl[id] is not None:
        await Pl[id].disconnect()
        Qu[ctx.message.guild.id].clear()
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command(pass_context=True, aliases=["r", "roll"])
async def _kosc(ctx, ilosc: int, kosc: int) -> None:
    await ctx.channel.purge(limit=1)
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


@bot.command(pass_context=True, aliases=["c", "clear"])
async def _czysc(ctx, num: int = 0) -> None:
    await ctx.channel.purge(limit=num + 1)


bot.run(TOKEN)  # type: ignore
