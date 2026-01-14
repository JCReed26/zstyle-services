"""
Base Input Channel Abstract Classes

This module defines the contract for all input channels in the ZStyle system.
Channels are responsible for:
1. Receiving input from external sources (Telegram, Discord, etc.)
2. Normalizing input to a standard format (NormalizedMessage)
3. Sending responses back to the source

KEY CONCEPTS:
=============
- BaseInputChannel: Basic contract for all channels
- ConversationalChannel: Extended base for human chat channels with keep-alive
- NormalizedMessage: Standard message format that flows to the agent layer

ADDING A NEW CHANNEL:
=====================

Step 1: Choose the right base class
    - Use BaseInputChannel for webhooks, API endpoints, automation triggers
    - Use ConversationalChannel for human chat interfaces (Telegram, Discord)

Step 2: Implement required methods
    
    ```python
    from channels.base import ConversationalChannel, NormalizedMessage, MessageType
    
    class MyChannel(ConversationalChannel):
        '''
        COPY-PASTE TEMPLATE for a new conversational channel.
        '''
        
        def __init__(self):
            super().__init__()
            # Initialize your client/SDK here
            self.client = None
        
        async def start(self) -> None:
            '''Initialize and start listening for messages.'''
            # Setup your SDK
            # Register message handlers
            pass
        
        async def stop(self) -> None:
            '''Graceful shutdown.'''
            # Close connections
            # Cleanup resources
            pass
        
        async def send_response(self, user_id: str, response: str) -> None:
            '''Send a response back to the user.'''
            # Use your SDK to send the message
            pass
        
        async def _handle_incoming(self, raw_event: Any) -> None:
            '''Process incoming message from your platform.'''
            # 1. Extract user info
            user_id = str(raw_event.user.id)
            
            # 2. Get conversation context (handles keep-alive)
            ctx = await self.get_or_create_context(user_id)
            
            # 3. Normalize the message
            message = NormalizedMessage(
                channel="my_channel",
                user_id=user_id,
                session_id=ctx.session_id,
                content_type=MessageType.TEXT,
                text=raw_event.text,
                attachments=[],
                raw_event=raw_event
            )
            
            # 4. Route to handler (set by router)
            if self._message_handler:
                await self._message_handler(message)
    ```

Step 3: Register with the system
    - Add to channels/__init__.py exports
    - Add to docker-compose.yml if it runs as a separate process
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Optional, List, Dict, Any, Awaitable
from enum import Enum
import uuid


class MessageType(Enum):
    """
    Types of content that can be received through channels.
    """
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"     # Voice message (audio transcribed)
    LOCATION = "location"
    CONTACT = "contact"


@dataclass
class NormalizedMessage:
    """
    Standard message format for all channels.
    
    This is the contract between channels and the agent layer.
    All channel-specific data is preserved in raw_event for special handling.
    
    Attributes:
        channel: Source channel identifier ("telegram", "api", etc.)
        user_id: Internal ZStyle user ID (may differ from channel's user ID)
        channel_user_id: Original user ID from the channel (for mapping)
        session_id: Conversation session ID (for context grouping)
        content_type: Type of content (text, image, audio, etc.)
        text: Text content (may be transcription for audio)
        attachments: Binary attachments (images, files)
        raw_event: Original channel-specific event object
        timestamp: When the message was received
    """
    channel: str
    user_id: str
    channel_user_id: str
    session_id: str
    content_type: MessageType
    text: Optional[str] = None
    attachments: List[bytes] = field(default_factory=list)
    attachment_urls: List[str] = field(default_factory=list)
    raw_event: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """
    Short-term conversation context for keep-alive functionality.
    
    This holds recent messages within the keep-alive window (default 300s).
    NOT persistent - stored in memory only.
    """
    session_id: str
    user_id: str
    last_activity: datetime
    messages: List[NormalizedMessage] = field(default_factory=list)
    
    def is_expired(self, keep_alive_seconds: int) -> bool:
        """Check if this context has expired."""
        elapsed = (datetime.utcnow() - self.last_activity).total_seconds()
        return elapsed >= keep_alive_seconds
    
    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def add_message(self, message: NormalizedMessage) -> None:
        """Add a message to the conversation history."""
        self.messages.append(message)
        self.touch()


# Type alias for message handlers
MessageHandler = Callable[[NormalizedMessage], Awaitable[str]]


class BaseInputChannel(ABC):
    """
    Abstract base class for all input channels.
    
    Use this for:
    - Webhooks (stateless, no conversation context)
    - API endpoints
    - Automation triggers
    
    For human chat interfaces, use ConversationalChannel instead.
    """
    
    def __init__(self):
        self._message_handler: Optional[MessageHandler] = None
    
    def set_message_handler(self, handler: MessageHandler) -> None:
        """
        Register the callback for when messages are received.
        
        The handler receives a NormalizedMessage and returns a response string.
        This is typically set by the MessageRouter.
        """
        self._message_handler = handler
    
    @abstractmethod
    async def start(self) -> None:
        """
        Initialize and start the channel.
        
        This should:
        - Setup SDK/client connections
        - Register event handlers
        - Begin listening for messages
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Gracefully shutdown the channel.
        
        This should:
        - Close connections
        - Cleanup resources
        - Cancel any pending tasks
        """
        pass
    
    @abstractmethod
    async def send_response(
        self,
        user_id: str,
        response: str,
        channel_user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send a response back through the channel.
        
        Args:
            user_id: Internal ZStyle user ID
            response: Text response to send
            channel_user_id: Original channel user ID (for routing)
            metadata: Optional channel-specific data (e.g., reply_to_message_id)
        """
        pass


class ConversationalChannel(BaseInputChannel):
    """
    Extended base class for human chat channels.
    
    Provides conversation keep-alive functionality:
    - Maintains context for KEEP_ALIVE_SECONDS (default 300s / 5 minutes)
    - After timeout, conversation context resets
    - This creates natural "conversation windows" without permanent history
    
    Use for:
    - Telegram
    - Discord
    - Slack
    - Any human-facing chat interface
    """
    
    # How long to keep conversation context alive (5 minutes)
    KEEP_ALIVE_SECONDS: int = 300
    
    def __init__(self):
        super().__init__()
        # user_id -> ConversationContext
        self._active_conversations: Dict[str, ConversationContext] = {}
    
    async def get_or_create_context(self, user_id: str) -> ConversationContext:
        """
        Get existing conversation context or create a new one.
        
        If the existing context has expired (no activity within KEEP_ALIVE_SECONDS),
        it will be replaced with a fresh context.
        
        Args:
            user_id: The user's ID
            
        Returns:
            ConversationContext for this user
        """
        now = datetime.utcnow()
        
        if user_id in self._active_conversations:
            ctx = self._active_conversations[user_id]
            if not ctx.is_expired(self.KEEP_ALIVE_SECONDS):
                ctx.touch()
                return ctx
            # Context expired - fall through to create new
        
        # Create fresh context
        new_ctx = ConversationContext(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            last_activity=now,
            messages=[]
        )
        self._active_conversations[user_id] = new_ctx
        return new_ctx
    
    def clear_context(self, user_id: str) -> None:
        """
        Manually clear a user's conversation context.
        
        Use for /newchat or similar commands.
        """
        if user_id in self._active_conversations:
            del self._active_conversations[user_id]
    
    def cleanup_expired_contexts(self) -> int:
        """
        Remove all expired conversation contexts.
        
        Call periodically to free memory. Returns count of removed contexts.
        """
        expired = [
            uid for uid, ctx in self._active_conversations.items()
            if ctx.is_expired(self.KEEP_ALIVE_SECONDS)
        ]
        for uid in expired:
            del self._active_conversations[uid]
        return len(expired)
