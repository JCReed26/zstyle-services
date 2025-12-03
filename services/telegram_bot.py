import os
import logging
import asyncio
import httpx
from typing import Dict, Optional
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Configuration
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Base URL for the ADK FastAPI app
API_BASE_URL = os.getenv("AGENT_URL", "http://localhost:8000")
AGENT_NAME = "exec_func_coach"

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory session store: chat_id -> session_id
# In a production app, this should be in a database (Redis/SQL)
USER_SESSIONS: Dict[int, str] = {}

async def get_or_create_session(chat_id: int, user_id: int) -> Optional[str]:
    """
    Retrieves an existing session ID or creates a new one via the ADK API.
    """
    if chat_id in USER_SESSIONS:
        return USER_SESSIONS[chat_id]

    # Create new session
    # Endpoint: POST /apps/{app_name}/users/{user_id}/sessions
    url = f"{API_BASE_URL}/apps/{AGENT_NAME}/users/{user_id}/sessions"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url)
            if response.status_code == 200:
                data = response.json()
                session_id = data.get("id")
                if session_id:
                    USER_SESSIONS[chat_id] = session_id
                    logger.info(f"Created new session {session_id} for chat {chat_id}")
                    return session_id
    except Exception as e:
        logger.error(f"Error creating session for chat {chat_id}: {e}")

    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /start command. Resets the session.
    """
    chat_id = update.effective_chat.id
    # Reset session on start to ensure a fresh experience
    if chat_id in USER_SESSIONS:
        del USER_SESSIONS[chat_id]
        
    welcome_text = (
        "Hello! I am your AI Executive Function Coach.\n\n"
        "I can help you manage your calendar, tasks, and reminders.\n"
        "Just chat with me naturally!\n\n"
        "Type /help to see what else I can do."
    )
    await update.message.reply_text(welcome_text)

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /newchat command. Clears session history.
    """
    chat_id = update.effective_chat.id
    if chat_id in USER_SESSIONS:
        del USER_SESSIONS[chat_id]
    
    await update.message.reply_text("Context cleared! Starting a new conversation.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /help command.
    """
    help_text = (
        "**Available Commands:**\n\n"
        "/start - Reset and start the bot\n"
        "/newchat - Start a new conversation context\n"
        "/help - Show this help message\n"
    )
    await update.message.reply_markdown(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles incoming messages by forwarding them to the ADK API.
    """
    if not update.effective_message:
        return

    chat_id = update.effective_message.chat_id
    user_id = str(update.effective_user.id)
    message_text = update.effective_message.text

    # Get or create session
    session_id = await get_or_create_session(chat_id, user_id)
    if not session_id:
        await update.effective_message.reply_text(
            "Sorry, I'm having trouble connecting to my brain. Please try again later."
        )
        return

    # Forward to ADK API
    # Endpoint: POST /run with message payload
    url = f"{API_BASE_URL}/run"
    payload = {
        "appName": AGENT_NAME,
        "userId": user_id,
        "sessionId": session_id,
        "newMessage": {
            "role": "user",
            "parts": [{"text": message_text}]
        }
    }

    # Indicate typing
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            
            # Handle Session Not Found (404) -> Retry with new session
            if response.status_code == 404:
                logger.warning(f"Session {session_id} not found on server. Creating new one.")
                if chat_id in USER_SESSIONS:
                    del USER_SESSIONS[chat_id]
                
                # Retry once
                session_id = await get_or_create_session(chat_id, user_id)
                if session_id:
                    payload["sessionId"] = session_id
                    response = await client.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                
                # Parse list of events to find the text response
                ai_response_text = ""
                if isinstance(data, list):
                    for event in data:
                        content = event.get("content")
                        if content and isinstance(content, dict):
                            parts = content.get("parts")
                            if parts and isinstance(parts, list):
                                for part in parts:
                                    text = part.get("text")
                                    if text:
                                        ai_response_text += text
                
                if not ai_response_text:
                    # Fallback if standard keys aren't found in a simple way
                    if isinstance(data, dict):
                        ai_response_text = data.get("text") or data.get("content")
                
                if ai_response_text:
                    await update.effective_message.reply_text(ai_response_text)
                else:
                    logger.info(f"No text response found in data: {data}")
            else:
                logger.error(f"Error from ADK API: {response.status_code} - {response.text}")
                await update.effective_message.reply_text("I'm having trouble thinking right now. Please check my logs.")
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
        await update.effective_message.reply_text("Sorry, I encountered an error processing your message.")


def main():
    """
    Main function to start the Telegram bot.
    """
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('newchat', new_chat))
    application.add_handler(CommandHandler('help', help_command))

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    logger.info(f"Starting Telegram Bot Interface (Agent URL: {API_BASE_URL})...")
    application.run_polling()


if __name__ == "__main__":
    main()