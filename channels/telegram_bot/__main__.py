"""
Telegram Bot Channel Entry Point

Allows running the channel as a module:
    python -m channels.telegram_bot
"""
import asyncio
from .channel import main

if __name__ == "__main__":
    asyncio.run(main())
