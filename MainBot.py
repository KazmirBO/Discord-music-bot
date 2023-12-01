#!/usr/bin/env python3

import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from yt_dlp.utils import asyncio

from cogs.AdminCog import AdminCog
from cogs.FunCog import FunCog
from cogs.MusicCog import MusicCog


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


async def main() -> None:
    await bot.add_cog(AdminCog(bot))
    await bot.add_cog(FunCog(bot))
    await bot.add_cog(MusicCog(bot))
    await bot.start(TOKEN)  # type: ignore


asyncio.run(main())
