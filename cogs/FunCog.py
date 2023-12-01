#!/usr/bin/env python3

import discord
import random
from discord.ext import commands


class FunCog(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot

    async def get_user_id(self, ctx) -> tuple:
        await ctx.channel.purge(limit=1)
        username = ctx.message.author.display_name
        id = ctx.message.guild.id
        return username, id

    @commands.command(pass_context=True, aliases=["r", "roll"])
    async def _kosc(self, ctx, ilosc: int, kosc: int) -> None:
        _, _ = await self.get_user_id(ctx=ctx)
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
