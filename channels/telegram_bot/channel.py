"""
Telegram Bot Channel Implementation

Implements ConversationalChannel for Telegram using python-telegram-bot.

Features:
- Text message handling
- Voice message handling (future: transcription)
- Image handling
- File handling
- Command handlers (/start, /newchat, /help, /logs)
- 300-second conversation keep-alive

ADDING NEW COMMANDS:
====================
1. Create a handler method:
    async def my_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Response")

2. Register in _setup_handlers():
    self.application.add_handler(CommandHandler('mycommand', self.my_command))

ADDING NEW MESSAGE TYPES:
=========================
1. Add handler in _setup_handlers() with appropriate filter
2. Create handler method that normalizes to NormalizedMessage
3. Route through self._message_handler
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import httpx

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    Application
)

from channels.base import (
    ConversationalChannel,
    NormalizedMessage,
    MessageType,
)
from database.engine import AsyncSessionLocal
from database.models import User
from sqlalchemy import select


logger = logging.getLogger(__name__)


class TelegramChannel(ConversationalChannel):
    """
    Telegram Bot implementation of ConversationalChannel.
    
    Handles:
    - Text messages -> routes to agent
    - Voice messages -> (future: transcribe then route)
    - Images -> routes with attachment
    - Commands -> special handling
    
    Conversation Context:
    - Maintains 300-second keep-alive (inherited from ConversationalChannel)
    - Fresh context created after timeout
    - /newchat command clears context manually
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Telegram channel.
        
        Args:
            token: Telegram bot token. If not provided, reads from TELEGRAM_BOT_TOKEN env var.
        """
        super().__init__()
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        self.application: Optional[Application] = None
        
        # Map telegram user IDs to internal user IDs
        self._user_id_cache: Dict[int, str] = {}
    
    async def start(self) -> None:
        """
        Initialize and start the Telegram bot.
        """
        logger.info("Starting Telegram channel...")
        
        # Build application
        self.application = ApplicationBuilder().token(self.token).build()
        
        # Setup handlers
        self._setup_handlers()
        
        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Telegram channel started successfully")
    
    async def stop(self) -> None:
        """
        Gracefully shutdown the Telegram bot.
        """
        logger.info("Stopping Telegram channel...")
        
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        logger.info("Telegram channel stopped")
    
    async def send_response(
        self,
        user_id: str,
        response: str,
        channel_user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send a response to a Telegram user.
        
        Args:
            user_id: Internal ZStyle user ID
            response: Text to send
            channel_user_id: Telegram chat ID (required for routing)
            metadata: Optional data (e.g., reply_to_message_id)
        """
        if not channel_user_id:
            logger.error(f"Cannot send response: no channel_user_id for user {user_id}")
            return
        
        chat_id = int(channel_user_id)
        
        reply_to = None
        if metadata and "reply_to_message_id" in metadata:
            reply_to = metadata["reply_to_message_id"]
        
        await self.application.bot.send_message(
            chat_id=chat_id,
            text=response,
            reply_to_message_id=reply_to
        )
    
    def _setup_handlers(self) -> None:
        """
        Register all message and command handlers.
        
        COPY-PASTE TEMPLATE for adding a new command:
        =============================================
        # 1. Add handler registration here:
        self.application.add_handler(CommandHandler('mycommand', self._cmd_mycommand))
        
        # 2. Create the handler method:
        async def _cmd_mycommand(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text("My response")
        """
        # Command handlers
        self.application.add_handler(CommandHandler('start', self._cmd_start))
        self.application.add_handler(CommandHandler('newchat', self._cmd_newchat))
        self.application.add_handler(CommandHandler('help', self._cmd_help))
        self.application.add_handler(CommandHandler('logs', self._cmd_logs))
        
        # Message handlers (order matters - more specific first)
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self._handle_photo)
        )
        self.application.add_handler(
            MessageHandler(filters.VIDEO, self._handle_video)
        )
        self.application.add_handler(
            MessageHandler(filters.VOICE | filters.AUDIO, self._handle_voice)
        )
        self.application.add_handler(
            MessageHandler(filters.Document.ALL, self._handle_document)
        )
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text)
        )
    
    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /start command.
        Welcomes user and resets conversation context.
        """
        telegram_id = update.effective_user.id
        
        # Clear conversation context
        user_id = await self._get_or_create_user(telegram_id, update.effective_user.username)
        self.clear_context(user_id)
        
        welcome = (
            "Hello! I'm your AI Executive Function Coach.\n\n"
            "I can help you:\n"
            "- Manage your goals and tasks\n"
            "- Organize your schedule\n"
            "- Track habits and progress\n"
            "- Access your Second Brain\n\n"
            "Just send me a message to get started!\n\n"
            "Commands:\n"
            "/newchat - Start fresh conversation\n"
            "/logs - View recent activity\n"
            "/help - Show this message"
        )
        await update.message.reply_text(welcome)
    
    async def _cmd_newchat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /newchat command.
        Clears conversation context for a fresh start.
        """
        telegram_id = update.effective_user.id
        user_id = await self._get_or_create_user(telegram_id)
        
        # Clear both channel context and router session
        self.clear_context(user_id)
        
        await update.message.reply_text(
            "Conversation cleared! Starting fresh.\n"
            "What would you like to work on?"
        )
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /help command.
        Shows available commands and capabilities.
        """
        help_text = (
            "**ZStyle Executive Function Coach**\n\n"
            "**Commands:**\n"
            "/start - Reset and show welcome\n"
            "/newchat - Clear conversation context\n"
            "/logs - View your last 25 activity logs\n"
            "/help - Show this message\n\n"
            "**I can help with:**\n"
            "- Goal setting and tracking\n"
            "- Task management\n"
            "- Calendar and scheduling\n"
            "- Habit tracking\n"
            "- Accessing your Second Brain\n\n"
            "Just send me a message!"
        )
        await update.message.reply_markdown(help_text)
    
    async def _cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /logs command.
        Shows user's recent activity logs.
        """
        from services.activity_log import activity_log_service
        
        telegram_id = update.effective_user.id
        user_id = await self._get_or_create_user(telegram_id)
        
        logs = await activity_log_service.get_recent(user_id, limit=25)
        
        if not logs:
            await update.message.reply_text("No activity logs found.")
            return
        
        formatted = activity_log_service.format_logs_for_display(logs)
        
        # Split if too long for Telegram (4096 char limit)
        if len(formatted) > 4000:
            formatted = formatted[:4000] + "\n... (truncated)"
        
        await update.message.reply_text(f"**Recent Activity:**\n\n```\n{formatted}\n```", parse_mode="Markdown")
    
    # =========================================================================
    # MESSAGE HANDLERS
    # =========================================================================
    
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming text messages.
        """
        if not update.effective_message or not update.effective_message.text:
            return
        
        telegram_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get or create user
        user_id = await self._get_or_create_user(telegram_id, update.effective_user.username)
        
        # Get conversation context (handles keep-alive)
        conv_ctx = await self.get_or_create_context(user_id)
        
        # Build normalized message
        message = NormalizedMessage(
            channel="telegram",
            user_id=user_id,
            channel_user_id=str(chat_id),
            session_id=conv_ctx.session_id,
            content_type=MessageType.TEXT,
            text=update.effective_message.text,
            attachments=[],
            raw_event=update,
            metadata={
                "message_id": update.effective_message.message_id,
                "telegram_user_id": telegram_id
            }
        )
        
        # Add to conversation history
        conv_ctx.add_message(message)
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Route to handler
        if self._message_handler:
            response = await self._message_handler(message)
            await self.send_response(
                user_id=user_id,
                response=response,
                channel_user_id=str(chat_id),
                metadata={"reply_to_message_id": update.effective_message.message_id}
            )
        else:
            logger.warning("No message handler registered for Telegram channel")
            await update.message.reply_text(
                "I'm not fully connected yet. Please try again later."
            )
    
    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming photo messages.
        """
        telegram_id = update.effective_user.id
        chat_id = update.effective_chat.id
        user_id = await self._get_or_create_user(telegram_id)
        conv_ctx = await self.get_or_create_context(user_id)
        
        # Get the largest photo
        photo = update.effective_message.photo[-1]  # Largest size
        file = await context.bot.get_file(photo.file_id)
        
        # Download photo bytes
        photo_bytes = await file.download_as_bytearray()
        
        # Get caption if any
        caption = update.effective_message.caption or ""
        
        message = NormalizedMessage(
            channel="telegram",
            user_id=user_id,
            channel_user_id=str(chat_id),
            session_id=conv_ctx.session_id,
            content_type=MessageType.IMAGE,
            text=caption,
            attachments=[bytes(photo_bytes)],
            raw_event=update,
            metadata={"file_id": photo.file_id}
        )
        
        conv_ctx.add_message(message)
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        if self._message_handler:
            response = await self._message_handler(message)
            await self.send_response(user_id, response, str(chat_id))
        else:
            await update.message.reply_text("I received your image but I'm not fully connected yet.")

    async def _handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming video messages.
        """
        telegram_id = update.effective_user.id
        chat_id = update.effective_chat.id
        user_id = await self._get_or_create_user(telegram_id)
        conv_ctx = await self.get_or_create_context(user_id)
        
        # We don't download the video yet to save bandwidth since we're just rejecting it
        # But we still track the interaction
        
        caption = update.effective_message.caption or ""
        
        # Create a placeholder message for history
        # We use content_type TEXT for now since we aren't processing the video content
        message = NormalizedMessage(
            channel="telegram",
            user_id=user_id,
            channel_user_id=str(chat_id),
            session_id=conv_ctx.session_id,
            content_type=MessageType.TEXT, 
            text=f"[User sent a video] {caption}",
            attachments=[],
            raw_event=update,
            metadata={"file_id": update.effective_message.video.file_id}
        )
        
        conv_ctx.add_message(message)
        
        # Add explicit logging to debug
        logger.info(f"Sending video apology to chat_id: {chat_id}")

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="I received your video message. Video analysis is coming soon! For now, please type your message."
            )
        except Exception as e:
            logger.error(f"Failed to send video apology: {e}")

    
    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming voice/audio messages.
        """
        telegram_id = update.effective_user.id
        chat_id = update.effective_chat.id
        user_id = await self._get_or_create_user(telegram_id)
        conv_ctx = await self.get_or_create_context(user_id)
        
        voice = update.effective_message.voice or update.effective_message.audio
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()
        
        # Determine mime type
        mime_type = voice.mime_type if hasattr(voice, 'mime_type') and voice.mime_type else "audio/ogg"
        
        message = NormalizedMessage(
            channel="telegram",
            user_id=user_id,
            channel_user_id=str(chat_id),
            session_id=conv_ctx.session_id,
            content_type=MessageType.VOICE,
            text=None,
            attachments=[bytes(audio_bytes)],
            raw_event=update,
            metadata={
                "file_id": voice.file_id, 
                "duration": voice.duration,
                "mime_type": mime_type
            }
        )
        
        conv_ctx.add_message(message)
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        if self._message_handler:
            response = await self._message_handler(message)
            await self.send_response(
                user_id=user_id, 
                response=response, 
                channel_user_id=str(chat_id),
                metadata={"reply_to_message_id": update.effective_message.message_id}
            )
        else:
            await update.message.reply_text(
                "I received your voice message but I'm not fully connected yet."
            )
    
    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming document/file messages.
        """
        telegram_id = update.effective_user.id
        chat_id = update.effective_chat.id
        user_id = await self._get_or_create_user(telegram_id)
        conv_ctx = await self.get_or_create_context(user_id)
        
        doc = update.effective_message.document
        file = await context.bot.get_file(doc.file_id)
        doc_bytes = await file.download_as_bytearray()
        
        caption = update.effective_message.caption or ""
        
        message = NormalizedMessage(
            channel="telegram",
            user_id=user_id,
            channel_user_id=str(chat_id),
            session_id=conv_ctx.session_id,
            content_type=MessageType.FILE,
            text=caption,
            attachments=[bytes(doc_bytes)],
            raw_event=update,
            metadata={
                "file_id": doc.file_id,
                "file_name": doc.file_name,
                "mime_type": doc.mime_type
            }
        )
        
        conv_ctx.add_message(message)
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        if self._message_handler:
            response = await self._message_handler(message)
            await self.send_response(user_id, response, str(chat_id))
        else:
            await update.message.reply_text("I received your file but I'm not fully connected yet.")
    
    # =========================================================================
    # USER MANAGEMENT
    # =========================================================================
    
    async def _get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None
    ) -> str:
        """
        Get or create internal user ID for a Telegram user.
        
        Maps Telegram user IDs to internal ZStyle user IDs.
        Creates a new user record if this is a first-time user.
        """
        # Check cache first
        if telegram_id in self._user_id_cache:
            return self._user_id_cache[telegram_id]
        
        async with AsyncSessionLocal() as db:
            # Check database
            result = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                self._user_id_cache[telegram_id] = user.id
                return user.id
            
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=username
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            self._user_id_cache[telegram_id] = user.id
            logger.info(f"Created new user {user.id} for Telegram ID {telegram_id}")
            return user.id


# =============================================================================
# STANDALONE RUNNER
# =============================================================================

async def main():
    """
    Run the Telegram channel as a standalone process.
    
    This is used when running as: python -m channels.telegram_bot
    """
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # For standalone mode, we need to connect to the ADK API
    # This is the HTTP Bridge Client implementation
    async def http_bridge_handler(message: NormalizedMessage) -> str:
        agent_url = os.getenv("AGENT_URL", "http://localhost:8000")
        endpoint = f"{agent_url}/api/chat"
        
        import base64
        
        # Encode attachments to Base64 strings
        encoded_attachments = []
        if message.attachments:
            for attach_bytes in message.attachments:
                encoded_attachments.append(base64.b64encode(attach_bytes).decode('utf-8'))
        
        # Construct payload matching BridgeRequest in main.py
        payload = {
            "channel": message.channel,
            "user_id": message.user_id,
            "channel_user_id": message.channel_user_id,
            "session_id": message.session_id,
            "content_type": message.content_type.value,
            "text": message.text,
            "attachments": encoded_attachments,
            "metadata": message.metadata
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"Bridge sending to {endpoint} for user {message.user_id}")
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "No response content.")
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Agent API returned error {e.response.status_code}: {e.response.text}")
            return f"I'm having trouble processing that (Error {e.response.status_code})."
        except Exception as e:
            logger.error(f"Bridge connection failed: {e}")
            return "I'm currently disconnected from my brain. Please check if the App service is running."
    
    channel = TelegramChannel()
    channel.set_message_handler(http_bridge_handler)
    
    try:
        await channel.start()
        logger.info("Telegram channel running. Press Ctrl+C to stop.")
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            # Cleanup expired contexts periodically
            cleaned = channel.cleanup_expired_contexts()
            if cleaned > 0:
                logger.debug(f"Cleaned up {cleaned} expired conversation contexts")
                
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await channel.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
