"""
Message Router

Bridges input channels to the ADK agent layer. Responsible for:
1. Receiving NormalizedMessage from channels
2. Converting to ADK-compatible format
3. Running the agent (memory handled by ADK Runner)
4. Logging activity
5. Returning response to channel

FLOW:
=====
Channel -> NormalizedMessage -> Router -> ADK Runner -> Response -> Channel

The router is the single point where channels connect to agents.
Agents never know which channel a message came from - they just see the content.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .base import NormalizedMessage, MessageType
from services.activity_log import activity_log_service
from core.database.models import ActivityLogSource


logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Routes messages from channels to the ADK agent layer.
    
    This is the bridge between the Communication Layer and Agent Layer.
    It handles:
    - Message format conversion
    - Agent invocation (memory handled by ADK Runner)
    - Activity logging
    
    Usage:
        # Setup
        router = MessageRouter(runner=my_runner)
        telegram_channel.set_message_handler(router.route)
        
        # Or manually route
        response = await router.route(normalized_message)
    """
    
    def __init__(
        self,
        runner: Runner,
        session_service: Optional[InMemorySessionService] = None,
        app_name: str = "zstyle"
    ):
        """
        Initialize the message router.
        
        Args:
            runner: ADK Runner instance with the root agent
            session_service: ADK session service (creates InMemory if not provided)
            app_name: Application name for session management
        """
        self.runner = runner
        self.session_service = session_service or InMemorySessionService()
        self.app_name = app_name
        
        # Track active ADK sessions per user
        # Note: This is separate from channel conversation contexts
        self._user_sessions: Dict[str, str] = {}
    
    async def route(self, message: NormalizedMessage) -> str:
        """
        Route a normalized message to the agent and return the response.
        
        This is the main entry point called by channels.
        
        Args:
            message: Normalized message from any channel
            
        Returns:
            Text response from the agent
        """
        user_id = message.user_id
        
        try:
            # 1. Log the incoming message
            await self._log_activity(message)
            
            # 2. Get or create ADK session
            session_id = await self._ensure_session(user_id)
            
            # 3. Build ADK content from message
            # Note: Memory is handled automatically by ADK Runner via MemoryService
            adk_content = self._build_adk_content(message)
            
            # 4. Run the agent
            response_text = await self._run_agent(user_id, session_id, adk_content)
            
            # 5. Log the response
            await activity_log_service.log(
                user_id=user_id,
                source=ActivityLogSource.SYSTEM,
                action=f"agent responded to {message.channel} message",
                extra_data={"response_length": len(response_text)}
            )
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error routing message for user {user_id}: {e}", exc_info=True)
            return "I'm sorry, I encountered an error processing your message. Please try again."
    
    async def _log_activity(self, message: NormalizedMessage) -> None:
        """Log the incoming message as activity."""
        # Map channel to activity source
        source_map = {
            "telegram": ActivityLogSource.TELEGRAM,
            "discord": ActivityLogSource.DISCORD,
            "api": ActivityLogSource.API,
            "webhook": ActivityLogSource.WEBHOOK,
        }
        source = source_map.get(message.channel, ActivityLogSource.SYSTEM)
        
        # Create action description
        if message.content_type == MessageType.TEXT:
            # Truncate long messages
            text_preview = (message.text or "")[:50]
            if len(message.text or "") > 50:
                text_preview += "..."
            action = f"user message: {text_preview}"
        else:
            action = f"user sent {message.content_type.value}"
        
        await activity_log_service.log(
            user_id=message.user_id,
            source=source,
            action=action,
            extra_data={
                "channel": message.channel,
                "content_type": message.content_type.value,
                "session_id": message.session_id
            }
        )
    
    async def _ensure_session(self, user_id: str) -> str:
        """
        Get existing ADK session or create a new one.
        
        Note: ADK sessions are lightweight - we create fresh ones rather than
        persisting long histories. User memory is handled by ADK Runner via MemoryService.
        """
        if user_id in self._user_sessions:
            # Verify session still exists
            try:
                session = await self.session_service.get_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=self._user_sessions[user_id]
                )
                if session:
                    return self._user_sessions[user_id]
            except Exception:
                pass
        
        # Create new session
        session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id
        )
        self._user_sessions[user_id] = session.id
        return session.id
    
    def _build_adk_content(
        self,
        message: NormalizedMessage
    ) -> types.Content:
        """
        Build ADK Content from normalized message.
        
        Memory/context is handled automatically by ADK Runner via MemoryService,
        so we just convert the message format here.
        """
        parts = []
        
        # Add text content
        if message.text:
            # Optionally prepend context (agents can also fetch this via tools)
            # For now, just pass the raw message
            parts.append(types.Part(text=message.text))
        
        # Handle other content types
        if message.content_type == MessageType.IMAGE and message.attachments:
            # Add image as inline data (if supported by model)
            for attachment in message.attachments:
                # Use metadata mime_type if available, else default to jpeg
                mime_type = message.metadata.get("mime_type", "image/jpeg")
                parts.append(types.Part(inline_data=types.Blob(
                    mime_type=mime_type,
                    data=attachment
                )))

        elif message.content_type == MessageType.VOICE and message.attachments:
            # Add audio as inline data
            for attachment in message.attachments:
                # Use metadata mime_type if available, else default to ogg (Telegram default)
                mime_type = message.metadata.get("mime_type", "audio/ogg")
                parts.append(types.Part(inline_data=types.Blob(
                    mime_type=mime_type,
                    data=attachment
                )))
        
        # TODO: Handle files
        
        return types.Content(role="user", parts=parts)
    
    async def _run_agent(
        self,
        user_id: str,
        session_id: str,
        content: types.Content
    ) -> str:
        """
        Run the agent and collect the response.
        
        Returns the final text response from the agent.
        """
        response_parts = []
        
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            # Collect final response events
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_parts.append(part.text)
        
        return "".join(response_parts) if response_parts else "I don't have a response for that."
    
    def clear_user_session(self, user_id: str) -> None:
        """
        Clear a user's ADK session (for /newchat commands).
        """
        if user_id in self._user_sessions:
            del self._user_sessions[user_id]
