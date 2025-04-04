#!/usr/bin/env python3

import discord as dc
from discord.ext import commands


class AdminCog(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
        self.man_page = [
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
                "+v/volume <procent>",
                "Wyświetla lub ustawia głośność (0-200%)",
                False,
            ],
            [
                "+l/lyrics",
                "Wyświetla tekst aktualnie odtwarzanego utworu",
                False,
            ],
            [
                "+lp/loop",
                "Włącza/wyłącza zapętlanie aktualnego utworu",
                False,
            ],
            [
                "+sp/saveplaylist <nazwa>",
                "Zapisuje aktualną kolejkę jako playlistę",
                False,
            ],
            [
                "+loadp/loadplaylist <nazwa>",
                "Wczytuje zapisaną playlistę",
                False,
            ],
            [
                "+pl/playlists",
                "Wyświetla listę dostępnych playlist",
                False,
            ],
            [
                "+autodj/similar <true/false>",
                "Włącza/wyłącza automatyczne dobieranie podobnych utworów",
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

    async def get_user_id(self, ctx) -> tuple:
        await ctx.channel.purge(limit=1)
        return ctx.message.author.display_name, ctx.message.guild.id

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot wystartowal!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        voice_state = member.guild.voice_client
        if voice_state is not None and len(voice_state.channel.members) == 1:
            await voice_state.disconnect()

    @commands.command(aliases=["h", "help", "man"], pass_context=False)
    async def _pomoc(self, ctx) -> None:
        _, _ = await self.get_user_id(ctx=ctx)
        embed = dc.Embed(
            title="Lista komend:",
            color=0x4DFF00,
        )
        embed.set_author(
            name="Manual",
        )
        for command in self.man_page:
            embed.add_field(
                name=command[0],
                value=command[1],
                inline=command[2],
            )

        await ctx.send(embed=embed)

    @commands.command(pass_context=True, aliases=["c", "clear"])
    async def _czysc(self, ctx, num: int = 0) -> None:
        try:
            await ctx.channel.purge(limit=num + 1)
        except Exception as e:
            await ctx.send(f"Wystąpił błąd: {e}")
