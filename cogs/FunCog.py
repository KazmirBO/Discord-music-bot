#!/usr/bin/env python3

import discord as dc
import random
from typing import Tuple
from discord.ext import commands
from config import BotConfig
from utils.user_manager import UserManager
from utils.logger import Logger


class FunCog(commands.Cog):
    """Entertainment and fun commands."""
    
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    async def get_user_id(self, ctx: commands.Context) -> Tuple[str, int]:
        """Get user info - delegated to UserManager."""
        return await UserManager.get_user_info(ctx)

    @commands.command(pass_context=True, aliases=["r", "roll"])
    async def dice_roll(self, ctx: commands.Context, ilosc: int, kosc: int) -> None:
        """Roll dice - format: +roll <number_of_dice> <die_type>."""
        try:
            username, _ = await self.get_user_id(ctx)
            
            # Validation
            if ilosc <= 0 or kosc <= 0:
                await ctx.send("❌ Liczba kości i rodzaj kości muszą być większe od 0.")
                return
            
            if ilosc > 20:
                await ctx.send("❌ Maksymalna liczba kości to 20.")
                return
            
            if kosc > 1000:
                await ctx.send("❌ Maksymalny rodzaj kości to 1000.")
                return
            
            # Roll dice
            rolls = [random.randint(1, kosc) for _ in range(ilosc)]
            total = sum(rolls)
            
            embed = dc.Embed(
                title="Rzut kością",
                color=BotConfig.COLORS["success"]
            )
            embed.set_author(name=f"Symulator rzutu kością {ilosc}d{kosc}")
            embed.add_field(name="Gracz", value=username, inline=True)
            embed.add_field(name="Suma", value=str(total), inline=True)
            embed.add_field(name="Średnia", value=f"{total/ilosc:.1f}", inline=True)
            
            # Show individual rolls if reasonable number
            if ilosc <= 10:
                for i, roll in enumerate(rolls, 1):
                    embed.add_field(
                        name=f"Kość {i}d{kosc}",
                        value=str(roll),
                        inline=True
                    )
            else:
                embed.add_field(
                    name="Wyniki",
                    value=f"Min: {min(rolls)}, Max: {max(rolls)}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            Logger.log_info(f"{username} rolled {ilosc}d{kosc}: {total}", "DICE_ROLL")
            
        except ValueError:
            await ctx.send("❌ Podaj prawidłowe liczby całkowite.")
        except Exception as e:
            Logger.log_error(e, "DICE_ROLL")
            await ctx.send("❌ Wystąpił błąd podczas rzutu kością.")
