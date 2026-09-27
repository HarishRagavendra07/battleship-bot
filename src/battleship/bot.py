"""Discord adapter: forwards chat messages to :class:`GameManager`."""

from __future__ import annotations

import io
import logging
import os

import discord
from dotenv import load_dotenv

from .commands import GameManager

log = logging.getLogger("battleship")


def create_client(manager: GameManager) -> discord.Client:
    intents = discord.Intents.default()
    intents.message_content = True  # required to read "bb ..." commands
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        log.info("Logged in as %s (id=%s)", client.user, client.user and client.user.id)

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return
        # One game per player per channel, so friends can play side by side.
        player = (message.channel.id, message.author.id)
        reply = manager.handle(player, message.content)
        if reply is None:
            return

        file = None
        if reply.image is not None:
            file = discord.File(io.BytesIO(reply.image), filename="board.png")
        await message.reply(reply.text, file=file, mention_author=False)

    return client


def main() -> None:
    load_dotenv()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN is not set. Copy .env.example to .env and add your bot token.")

    style = os.environ.get("BB_BOARD_STYLE", "image")
    client = create_client(GameManager(board_style=style))
    client.run(token)


if __name__ == "__main__":
    main()
