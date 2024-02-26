#!/usr/bin/env python3

import discord as dc
import os
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

from cogs.AdminCog import AdminCog
from cogs.FunCog import FunCog
from cogs.MusicCog import MusicCog


class MusicBot:
    def __init__(self):
        super().__init__()
        load_dotenv()
        self.TOKEN = os.getenv("TOKEN")

        command_prefix = "+"
        intents = dc.Intents.all()
        intents.message_content = True
        help_command = None
        case_intensive = None

        self.bot = commands.Bot(
            command_prefix=command_prefix,
            intents=intents,
            help_command=help_command,
            case_intensive=case_intensive,
        )

        asyncio.run(self.main())

    async def main(self) -> None:
        await self.bot.add_cog(AdminCog(bot=self.bot))
        await self.bot.add_cog(FunCog(bot=self.bot))
        await self.bot.add_cog(MusicCog(bot=self.bot))
        await self.bot.start(token=self.TOKEN)  # type: ignore


MusicBot()
