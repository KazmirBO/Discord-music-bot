#!/usr/bin/env python3

import discord as dc
from typing import List, Tuple
from discord.ext import commands
from config import BotConfig
from utils.user_manager import UserManager
from utils.logger import Logger


class AdminCog(commands.Cog):
    """Administrative commands and bot management."""
    
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.man_page: List[Tuple[str, str, bool]] = [
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

    async def get_user_id(self, ctx: commands.Context) -> Tuple[str, int]:
        """Get user info - delegated to UserManager."""
        return await UserManager.get_user_info(ctx)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Bot startup event."""
        Logger.log_info("Bot wystartował!", "STARTUP")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, 
        member: dc.Member, 
        before: dc.VoiceState, 
        after: dc.VoiceState
    ) -> None:
        """Auto-disconnect when bot is alone in voice channel."""
        voice_state = member.guild.voice_client
        if voice_state is not None and len(voice_state.channel.members) == 1:
            Logger.log_info(f"Auto-disconnecting from {voice_state.channel.name} (no users)", "VOICE")
            await voice_state.disconnect()

    @commands.command(aliases=["h", "help", "man"], pass_context=False)
    async def help_command(self, ctx: commands.Context) -> None:
        """Display help information."""
        await self.get_user_id(ctx)
        
        embed = dc.Embed(
            title="Lista komend:",
            color=BotConfig.COLORS["success"]
        )
        embed.set_author(name="Manual")
        
        for command in self.man_page:
            embed.add_field(
                name=command[0],
                value=command[1],
                inline=command[2]
            )
        
        await ctx.send(embed=embed)

    @commands.command(pass_context=True, aliases=["c", "clear"])
    async def clear_messages(self, ctx: commands.Context, num: int = 0) -> None:
        """Clear specified number of messages from channel."""
        try:
            if num <= 0:
                await ctx.send("❌ Podaj liczbę wiadomości do usunięcia (większą od 0).")
                return
            
            if num > 100:
                await ctx.send("❌ Maksymalna liczba wiadomości do usunięcia to 100.")
                return
            
            deleted = await ctx.channel.purge(limit=num + 1)
            Logger.log_info(
                f"Cleared {len(deleted)-1} messages in {ctx.channel.name}", 
                f"CLEAR_BY_{ctx.author.display_name}"
            )
        except dc.Forbidden:
            await ctx.send("❌ Brak uprawnień do usuwania wiadomości.")
        except dc.HTTPException as e:
            Logger.log_error(e, "CLEAR_MESSAGES")
            await ctx.send(f"❌ Wystąpił błąd podczas usuwania wiadomości.")
        except Exception as e:
            Logger.log_error(e, "CLEAR_MESSAGES_UNEXPECTED")
            await ctx.send(f"❌ Nieoczekiwany błąd: {e}")
