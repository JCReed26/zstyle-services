"""
ZStyle Channels Package

Input Channel Abstraction Layer for the ZStyle system.

This package provides a unified interface for all communication channels
(Telegram, Discord, CLI, Webhooks, etc.) to interact with the agent layer.

Architecture:
    1. BaseInputChannel - ABC defining the channel contract
    2. ConversationalChannel - Extended base for human chat channels (with keep-alive)
    3. MessageRouter - Bridges channels to the ADK agent layer

ADDING A NEW CHANNEL:
=====================
1. Create a new directory: channels/your_channel/
2. Implement BaseInputChannel or ConversationalChannel
3. Register in MessageRouter if needed

Example:
    from channels.base import ConversationalChannel, NormalizedMessage
    
    class DiscordChannel(ConversationalChannel):
        async def start(self) -> None:
            # Initialize Discord client
            pass
        
        async def stop(self) -> None:
            # Cleanup
            pass
        
        async def send_response(self, user_id: str, response: str) -> None:
            # Send to Discord
            pass
"""
from .base import (
    BaseInputChannel,
    ConversationalChannel,
    NormalizedMessage,
    MessageType,
    ConversationContext,
)
from .router import MessageRouter

__all__ = [
    "BaseInputChannel",
    "ConversationalChannel", 
    "NormalizedMessage",
    "MessageType",
    "ConversationContext",
    "MessageRouter",
]
