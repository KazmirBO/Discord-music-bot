#!/usr/bin/env python3

import discord
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
        username = ctx.message.author.display_name
        id = ctx.message.guild.id
        return username, id

    @commands.command(aliases=["h", "help", "man"], pass_context=False)
    async def _pomoc(self, ctx) -> None:
        _, _ = await self.get_user_id(ctx=ctx)
        embed = discord.Embed(
            title="Lista komend:",
            color=0x4DFF00,
        )
        embed.set_author(
            name="Manual",
        )
        for iter in self.man_page:
            embed.add_field(
                name=iter[0],
                value=iter[1],
                inline=iter[2],
            )

        await ctx.send(embed=embed)

    @commands.command(pass_context=True, aliases=["c", "clear"])
    async def _czysc(self, ctx, num: int = 0) -> None:
        await ctx.channel.purge(limit=num + 1)


def setup(bot) -> None:
    bot.add_cog(AdminCog(bot))
