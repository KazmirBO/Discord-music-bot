#!/usr/bin/env python3

import discord as dc
import random
from discord.ext import commands


class FunCog(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.command(pass_context=True, aliases=["r", "roll"])
    async def _rzut_koscia(self, ctx, ilosc: int, kosc: int) -> None:
        embed = dc.Embed(
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
