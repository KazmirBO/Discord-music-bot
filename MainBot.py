#!/usr/bin/env python3

import discord
import os
from discord.ext import commands
from dotenv import load_dotenv


async def setup_bot() -> None:
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

    await bot.load_extension("music_cog")
    await bot.load_extension("fun_cog")
    await bot.load_extension("admin_cog")

    @bot.event
    async def on_ready():
        print("Bot wystartował!")

    @bot.event
    async def on_voice_state_update(member, before, after):
        del after, before
        voice_state = member.guild.voice_client
        if voice_state is not None and len(voice_state.channel.members) == 1:
            await voice_state.disconnect()

    bot.run(TOKEN)  # type: ignore


await setup_bot()
