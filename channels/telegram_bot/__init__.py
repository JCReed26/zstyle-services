"""
Telegram Bot Channel

Implements the ConversationalChannel interface for Telegram.

Usage:
    from channels.telegram_bot import TelegramChannel
    
    channel = TelegramChannel(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    channel.set_message_handler(router.route)
    await channel.start()
"""
from .channel import TelegramChannel

__all__ = ["TelegramChannel"]
