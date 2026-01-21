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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, BotCommand, KeyboardButton, ReplyKeyboardMarkup
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
from database.repositories import UserRepository
from database.availability import is_database_available


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
        
        Note: For webhook mode, initialize() and start() are called separately.
        This method is kept for backward compatibility with polling mode.
        """
        logger.info("Starting Telegram channel...")
        
        # Build application
        self.application = ApplicationBuilder().token(self.token).build()
        
        # Setup handlers
        self._setup_handlers()
        
        # Initialize and start (without polling for webhook mode)
        await self.application.initialize()
        await self.application.start()
        
        # Register bot commands so they appear in the menu
        await self._register_commands()
        
        # For polling mode, call: await self.application.updater.start_polling()
        
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
    
    async def _register_commands(self) -> None:
        """Register bot commands with Telegram so they appear in the menu."""
        commands = [
            BotCommand("start", "Start the bot and authenticate"),
            BotCommand("help", "Show help and available commands"),
            BotCommand("authorize", "Authorize services (Google, TickTick)")
        ]
        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot commands registered successfully")
        except Exception as e:
            logger.error(f"Failed to register bot commands: {e}", exc_info=True)
    
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
        self.application.add_handler(CommandHandler('help', self._cmd_help))
        self.application.add_handler(CommandHandler('authorize', self._cmd_authorize))
        
        # Contact handler (for phone number sharing)
        self.application.add_handler(
            MessageHandler(filters.CONTACT, self._handle_contact)
        )
        
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
        Checks if user exists, if not prompts for phone number sharing.
        """
        telegram_id, username, phone_number = self._extract_telegram_user_info(update)
        chat_id = update.effective_chat.id
        
        # Check if user exists
        user_exists = await self._check_user_exists(telegram_id)
        
        if user_exists:
            # User exists - welcome them
            user_id = await self._get_or_create_user(telegram_id, username, phone_number)
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
                "/help - Show help message"
            )
            await update.message.reply_text(welcome)
        else:
            # User doesn't exist - prompt for authentication
            await self._prompt_phone_auth(update, context)
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /help command.
        Shows available commands and capabilities.
        """
        help_text = (
            "**ZStyle Executive Function Coach**\n\n"
            "**Commands:**\n"
            "/start - Start the bot and authenticate\n"
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
    
    async def _cmd_authorize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle /authorize command.
        Shows Web App button for OAuth authorization.
        """
        telegram_id, username, phone_number = self._extract_telegram_user_info(update)
        
        # Verify user is properly authenticated (not using temporary UUID)
        # Check if user_id looks like a temporary UUID (from _get_or_create_user fallback)
        if not await self._check_user_exists(telegram_id):
            await update.message.reply_text(
                "❌ Please authenticate first using /start and share your phone number.\n\n"
                "OAuth requires a verified user account."
            )
            return
        
        user_id = await self._get_or_create_user(telegram_id, username, phone_number)
        
        # Get base URL from settings with validation
        from app.config import settings
        
        base_url = settings.OAUTH_BASE_URL
        if not base_url:
            await update.message.reply_text(
                "❌ OAuth is not configured. Please set OAUTH_BASE_URL in your .env file.\n\n"
                "For development with ngrok:\n"
                "1. Start ngrok: make ngrok-start\n"
                "2. Restart the application to load the new URL"
            )
            return
        
        if not base_url.startswith("https://"):
            await update.message.reply_text(
                "❌ OAUTH_BASE_URL must be HTTPS. Telegram Mini Apps require secure connections.\n\n"
                f"Current value: {base_url}"
            )
            return
        
        base_url = base_url.rstrip('/')
        
        # Create Web App buttons for available services
        buttons = []
        
        # Google OAuth button
        if settings.GOOGLE_CLIENT_ID:
            google_url = f"{base_url}/oauth/webapp?service=google&user_id={user_id}"
            buttons.append([
                InlineKeyboardButton(
                    "🔍 Authorize Google",
                    web_app=WebAppInfo(url=google_url)
                )
            ])
        
        # TickTick OAuth button
        if settings.TICKTICK_CLIENT_ID:
            ticktick_url = f"{base_url}/oauth/webapp?service=ticktick&user_id={user_id}"
            buttons.append([
                InlineKeyboardButton(
                    "✓ Authorize TickTick",
                    web_app=WebAppInfo(url=ticktick_url)
                )
            ])
        
        if not buttons:
            await update.message.reply_text(
                "No OAuth services are configured. Please contact the administrator."
            )
            return
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await update.message.reply_text(
            "Click a button below to authorize a service:\n\n"
            "This will open a secure authorization page where you can grant access to your accounts.",
            reply_markup=keyboard
        )

    # =========================================================================
    # MESSAGE HANDLERS
    # =========================================================================
    
    # TODO: Implement the text cleaning functionality and add step to send_response
    def _clean_text(self, text: str) -> str:
        """Cleans markdown syntax from ADK and manipulates to Telegram"""
        pass

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming text messages.
        """
        if not update.effective_message or not update.effective_message.text:
            return
        
        telegram_id, username, phone_number = self._extract_telegram_user_info(update)
        chat_id = update.effective_chat.id
        
        # Check if user is authenticated
        user_id = await self._ensure_user_authenticated(telegram_id, username, phone_number)
        
        if not user_id:
            # User not authenticated - prompt for auth
            await self._prompt_phone_auth(update, context)
            return
        
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
        
        # Check if user is authenticated
        user_id = await self._ensure_user_authenticated(telegram_id)
        if not user_id:
            await self._prompt_phone_auth(update, context)
            return
        
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
        
        # Check if user is authenticated
        user_id = await self._ensure_user_authenticated(telegram_id)
        if not user_id:
            await self._prompt_phone_auth(update, context)
            return
        
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
        
        # Check if user is authenticated
        user_id = await self._ensure_user_authenticated(telegram_id)
        if not user_id:
            await self._prompt_phone_auth(update, context)
            return
        
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
        
        # Check if user is authenticated
        user_id = await self._ensure_user_authenticated(telegram_id)
        if not user_id:
            await self._prompt_phone_auth(update, context)
            return
        
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
    
    def _extract_telegram_user_info(self, update: Update) -> tuple[int, Optional[str], Optional[str]]:
        """
        Extract user information from Telegram update.
        
        Returns:
            Tuple of (telegram_id, username, phone_number)
        """
        telegram_user = update.effective_user
        telegram_id = telegram_user.id
        username = telegram_user.username
        phone_number = getattr(telegram_user, 'phone_number', None)
        return telegram_id, username, phone_number
    
    async def _check_user_exists(self, telegram_id: int) -> bool:
        """
        Check if a user exists by Telegram ID.
        
        Returns:
            True if user exists, False otherwise
        """
        if not is_database_available():
            return False
        
        try:
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                user = await repo.get_by_telegram_id(telegram_id)
                return user is not None
        except Exception as e:
            logger.error(f"Error checking user existence: {e}", exc_info=True)
            return False
    
    async def _ensure_user_authenticated(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Optional[str]:
        """
        Ensure user is authenticated before processing messages.
        
        Returns:
            User ID if authenticated, None if not authenticated
        """
        user_exists = await self._check_user_exists(telegram_id)
        
        if not user_exists:
            return None
        
        return await self._get_or_create_user(telegram_id, username, phone_number)
    
    async def _prompt_phone_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Prompt user to share their phone number for authentication.
        """
        from app.config import settings
        
        # Create contact request button
        keyboard = [
            [
                KeyboardButton(
                    "📱 Share Phone Number",
                    request_contact=True
                )
            ]
        ]
        
        # Optionally add Web App button for phone auth
        base_url = settings.OAUTH_BASE_URL or f"https://localhost:{settings.PORT}"
        if base_url and not base_url.startswith("https://"):
            base_url = f"https://localhost:{settings.PORT}"
        base_url = base_url.rstrip('/')
        webapp_url = f"{base_url}/auth/phone?telegram_id={update.effective_user.id}"
        
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Also create inline keyboard with Web App option
        inline_keyboard = [
            [
                InlineKeyboardButton(
                    "🔐 Authenticate via Web App",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]
        ]
        inline_markup = InlineKeyboardMarkup(inline_keyboard)
        
        message_text = (
            "👋 Welcome to ZStyle!\n\n"
            "To get started, please authenticate with your phone number.\n\n"
            "You can either:\n"
            "1. Share your phone number using the button below, or\n"
            "2. Use the Web App to enter your phone number and verify with OTP\n\n"
            "Your phone number is used for secure authentication only."
        )
        
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup
        )
        
        # Send separate message with inline button
        await update.message.reply_text(
            "Or use the Web App:",
            reply_markup=inline_markup
        )
    
    async def _handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle shared contact (phone number) for authentication.
        Creates user immediately - no OTP verification.
        Relies on Telegram's built-in contact verification.
        """
        telegram_id = update.effective_user.id
        chat_id = update.effective_chat.id
        contact = update.message.contact
        
        # Verify the contact belongs to the user (Telegram's built-in protection)
        if contact.user_id != telegram_id:
            await update.message.reply_text(
                "Please share your own phone number for authentication."
            )
            return
        
        phone_number = contact.phone_number
        # Ensure phone number is in E.164 format
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        try:
            from services.auth_service import auth_service
            
            # Create user immediately
            result = await auth_service.create_user_with_phone(
                phone_number=phone_number,
                telegram_id=telegram_id,
                telegram_username=update.effective_user.username
            )
            
            user_id = result['user_id']
            
            # Update cache
            self._user_id_cache[telegram_id] = user_id
            
            await update.message.reply_text(
                "✅ Authentication successful!\n\n"
                "You're now ready to use ZStyle. Send me a message to get started!"
            )
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Failed to create account. Please try again or use /start."
            )
    
    async def _get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> str:
        """
        Get or create internal user ID for a Telegram user.
        
        Gets or creates user account. Users authenticate by sharing their phone number
        via Telegram contact, which is verified by Telegram.
        
        Supports graceful degradation - returns temporary ID if database unavailable.
        
        Args:
            telegram_id: Telegram user ID
            username: Optional Telegram username
            phone_number: Optional phone number from Telegram user (E.164 format)
                        (used for linking, but user must authenticate via OTP first)
        
        Returns:
            User ID (UUID string from auth.users.id) or temporary ID if database unavailable
        
        Raises:
            ValueError: If user not found and needs to authenticate
        """
        # Check cache first
        if telegram_id in self._user_id_cache:
            return str(self._user_id_cache[telegram_id])
        
        # If database unavailable, return temporary ID
        if not is_database_available():
            logger.warning(
                f"Database unavailable - using temporary ID for Telegram user {telegram_id}. "
                "User should authenticate when database is available."
            )
            import uuid
            temp_id = str(uuid.uuid4())
            self._user_id_cache[telegram_id] = temp_id
            return temp_id
        
        try:
            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                
                # Check if user exists by Telegram ID
                user = await repo.get_by_telegram_id(telegram_id)
                
                if user:
                    # User exists - update username if needed
                    if username and user.username != username:
                        try:
                            user = await repo.update(user.id, username=username)
                        except Exception as e:
                            logger.warning(f"Failed to update username: {e}")
                    self._user_id_cache[telegram_id] = user.id
                    return str(user.id)
                
                # User doesn't exist - they need to authenticate via phone first
                # User authentication is handled via phone number sharing
                logger.warning(
                    f"User with Telegram ID {telegram_id} not found. "
                    "User must authenticate via phone OTP first. "
                    "Returning temporary ID - user should authenticate via /auth command."
                )
                
                # Return a temporary identifier
                # This allows the system to continue, but user should authenticate
                # The temporary ID will be replaced after phone auth completes
                import uuid
                temp_id = str(uuid.uuid4())
                self._user_id_cache[telegram_id] = temp_id
                
                return temp_id
        except Exception as e:
            logger.error(f"Database error in _get_or_create_user: {e}", exc_info=True)
            # Return temporary ID as fallback
            import uuid
            temp_id = str(uuid.uuid4())
            self._user_id_cache[telegram_id] = temp_id
            return temp_id
    
    async def link_telegram_to_user(
        self,
        user_id: str,
        telegram_id: int,
        username: Optional[str] = None
    ) -> None:
        """
        Link Telegram ID to an authenticated user.
        
        This is called after a user authenticates via phone OTP.
        
        Args:
            user_id: UUID from auth.users.id (string)
            telegram_id: Telegram user ID
            username: Optional Telegram username
        """
        from services.auth_service import auth_service
        
        try:
            await auth_service.link_telegram_id(
                user_id=user_id,
                telegram_id=telegram_id,
                telegram_username=username
            )
            
            # Update cache
            self._user_id_cache[telegram_id] = user_id
            logger.info(f"Linked Telegram ID {telegram_id} to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to link Telegram ID: {e}", exc_info=True)
            raise
    
    # =========================================================================
    # WEBHOOK SUPPORT
    # =========================================================================
    
    async def process_webhook_update(self, update: Update) -> None:
        """
        Process a Telegram update received via webhook.
        
        Routes the update through appropriate handlers based on content type.
        This method is called by the webhook endpoint to process updates.
        
        Args:
            update: Telegram Update object parsed from webhook JSON
        
        Raises:
            ValueError: If application is not initialized
        """
        if not self.application:
            raise ValueError("TelegramChannel application not initialized. Call start() first.")
        
        # Create a minimal context object for handlers
        # Handlers need context.bot for send_chat_action and get_file operations
        class WebhookContext:
            """Minimal context object for webhook updates."""
            def __init__(self, bot):
                self.bot = bot
        
        context = WebhookContext(self.application.bot)
        
        # Route update based on type
        if update.message:
            message = update.message
            
            # Check for commands first
            if message.text and message.entities:
                for entity in message.entities:
                    if entity.type == "bot_command":
                        command = message.text[entity.offset:entity.offset + entity.length].split("@")[0]
                        
                        # Route to command handler
                        if command == "/start":
                            await self._cmd_start(update, context)
                        elif command == "/help":
                            await self._cmd_help(update, context)
                        return
            
            # Route to message handlers based on content type
            if message.photo:
                await self._handle_photo(update, context)
            elif message.video:
                await self._handle_video(update, context)
            elif message.voice or message.audio:
                await self._handle_voice(update, context)
            elif message.document:
                await self._handle_document(update, context)
            elif message.text:
                await self._handle_text(update, context)
        
        elif update.callback_query:
            # Handle callback queries (for inline keyboards)
            # TODO: Implement callback query handlers if needed
            logger.debug(f"Received callback_query update: {update.callback_query.data}")
        
        else:
            logger.debug(f"Unhandled update type: {update.update_id}")


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
        # Start polling to receive messages from Telegram
        logger.info("Starting Telegram polling...")
        await channel.application.updater.start_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
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
