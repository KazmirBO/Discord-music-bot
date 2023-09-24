#!/usr/bin/env python3

import datetime
from random import randint
import yt_dlp
import discord
import os
from discord.ext import commands, tasks
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="+", intents=intents, help_command=None)

ydl_opts = {
    "format": "bestaudio[ext=webm]/best",
    "noplaylist": True,
    "outtmpl": "%(id)s.%(ext)s",
    # "postprocessors": [
    #     {
    #         "key": "FFmpegExtractAudio",
    #         # "preferredcodec": "webm",
    #         "preferredquality": "192",
    #     }
    # ],
}
Queue = []

load_dotenv()
TOKEN = os.getenv("TOKEN")


@bot.event
async def on_ready() -> None:
    print("Bot wystartował!")


@bot.command()
async def man(ctx) -> None:
    embed = discord.Embed(
        title="Lista komend:",
        color=0x4DFF00,
    )
    embed.set_author(
        name="Manual",
    )
    embed.add_field(
        name="+man",
        value="Wyświetla to okno pomocy",
        inline=True,
    )
    embed.add_field(
        name="+play <url>",
        value="Odtwarza utwór z podanego <url> albo dodaje do kolejki",
        inline=True,
    )
    embed.add_field(
        name="+pause",
        value="Wstrzymuje/Wznawia utwór",
        inline=True,
    )
    embed.add_field(
        name="+skip <numer>",
        value="Odtwarza następny utwór z kolejki \
        (jeżeli wpisałeś <numer> odtwarza wybrany utwór)",
        inline=True,
    )
    embed.add_field(
        name="+queue",
        value="Wyświetla kolejkę odtwarzania",
        inline=True,
    )
    embed.add_field(
        name="+stop",
        value="Zatrzymuje odtwarzanie utworu",
        inline=True,
    )
    embed.add_field(
        name="+disconnect",
        value="Rozłącza Bota",
        inline=True,
    )
    embed.add_field(
        name="+roll <ilość kości> <rodzaj kości>",
        value="Wykonuje prosty rzut kością, np. \
        +roll 1 6, rzut kością sześcienną",
        inline=True,
    )
    embed.add_field(
        name="+clear <numer>",
        value="Usuwa <numer> wiadomości z kanału",
        inline=True,
    )
    await ctx.send(embed=embed)


@bot.command()
async def play(ctx, url: str) -> None:
    vs = ctx.author.voice
    await ctx.channel.purge(limit=1)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    username = ctx.message.author.display_name
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
        value=url,
        inline=False,
    )
    await ctx.send(embed=embed)
    if vs:
        voice_channel = vs.channel
        if not ctx.voice_client:
            vc = await voice_channel.connect()
        else:
            vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        Queue.append(
            {
                "url": url,
                "url2": info["url"],  # type: ignore
                "title": info["title"],  # type: ignore
                "uploader": info["uploader"],  # type: ignore
                "duration": info["duration"],  # type: ignore
                "id": info["id"],  # type: ignore
                "user": username,
            }
        )
        if not vc.is_playing():  # type: ignore
            await play_next(ctx, vc)
    else:
        await ctx.send("Najpierw dołącz do kanału głosowego.")


@tasks.loop(seconds=5.0)
async def music_loop(ctx):
    print("Loop")
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not vc.is_playing() and vc:  # type: ignore
        await play_next(ctx, vc)


async def play_next(ctx, vc, pos: int = 0) -> None:
    if Queue:
        info = Queue.pop(pos)
        try:
            vc.play(discord.FFmpegPCMAudio(f"./{info['id']}.webm"))
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
                value=info["url"],
                inline=False,
            )
            await ctx.send(embed=embed)
            music_loop.start(ctx)
        except Exception as err:
            print(f"Wystąpił błąd: {err=}, {type(err)=}")
    else:
        await vc.disconnect()


@bot.command()
async def skip(ctx, pos: int = 1) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None:
        if len(Queue) >= pos:
            if vc.is_playing():  # type: ignore
                vc.stop()  # type: ignore
            await play_next(ctx, vc, pos - 1)
        else:
            await ctx.send("Kolejka jest pusta.")
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command()
async def queue(ctx) -> None:
    if Queue:
        embed = discord.Embed(
            title="Kolejka odtwarzania:",
            color=discord.Colour.random(),
        )
        for i, info in enumerate(Queue, start=1):
            embed.add_field(
                name=f"Utwór w kolejce: {i}",
                value=f"{info['title']}\n{info['uploader']}\n{str(datetime.timedelta(seconds=int(info['duration'])))}\n{info['url']}",
                inline=False,
            )
        await ctx.send(embed=embed)
    else:
        await ctx.send("Kolejka jest pusta.")


@bot.command()
async def pause(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None:
        if vc.is_playing():  # type: ignore
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


@bot.command()
async def stop(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None:
        if vc.is_playing():  # type: ignore
            vc.stop()  # type: ignore
            Queue.clear()
    else:
        await ctx.send("Nie ma czego zatrzymać.")


@bot.command()
async def disconnect(ctx) -> None:
    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if vc is not None:
        await vc.disconnect()  # type: ignore
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")


@bot.command()
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
            name="Kość: " + str(i + 1),
            value=randint(1, kosc),
        )
    await ctx.send(embed=embed)


@bot.command()
async def clear(ctx, num: int = 0):
    await ctx.channel.purge(limit=num + 1)


bot.run(TOKEN)  # type: ignore
