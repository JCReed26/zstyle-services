"""
Telegram Webhook Endpoint

Receives webhook updates from Telegram and routes them through TelegramChannel.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Request, Header, HTTPException

# Import Update - handle package conflict gracefully
try:
    from telegram import Update
except ImportError:
    # Fallback if there's a package conflict (telegram vs python-telegram-bot)
    # Try importing from python_telegram_bot directly
    try:
        import python_telegram_bot as ptb
        Update = ptb.Update
    except (ImportError, AttributeError):
        # If that fails, we'll get a proper error when Update is used
        Update = None

from core.config import settings
from channels.telegram_bot import TelegramChannel


logger = logging.getLogger(__name__)

router = APIRouter()

# Global TelegramChannel instance (set from main.py)
_telegram_channel: Optional[TelegramChannel] = None


def set_telegram_channel(channel: TelegramChannel) -> None:
    """
    Set the TelegramChannel instance for webhook processing.
    
    Called from main.py during application startup.
    """
    global _telegram_channel
    _telegram_channel = channel
    logger.info("TelegramChannel instance set for webhook processing")


@router.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """
    Telegram webhook endpoint.
    
    Receives updates from Telegram and processes them through TelegramChannel.
    
    Args:
        request: FastAPI request object containing JSON body
        x_telegram_bot_api_secret_token: Secret token header for webhook verification
    
    Returns:
        {"ok": True} on success
    
    Raises:
        HTTPException: 401 if secret token is invalid, 500 if processing fails
    """
    # Verify secret token if configured
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if not x_telegram_bot_api_secret_token:
            logger.warning("Webhook request missing secret token")
            raise HTTPException(status_code=401, detail="Invalid secret token")
        
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Webhook request with invalid secret token")
            raise HTTPException(status_code=401, detail="Invalid secret token")
    
    # Check if TelegramChannel is initialized
    if _telegram_channel is None:
        logger.error("TelegramChannel not initialized for webhook processing")
        raise HTTPException(status_code=500, detail="Webhook service not available")
    
    try:
        # Parse JSON body
        data = await request.json()
        
        # Parse Update object from JSON
        # bot=None because we don't need bot instance for parsing
        update = Update.de_json(data, bot=None)
        
        if update is None:
            logger.warning("Failed to parse Update from webhook JSON")
            raise HTTPException(status_code=400, detail="Invalid update format")
        
        # Process update through TelegramChannel
        await _telegram_channel.process_webhook_update(update)
        
        return {"ok": True}
        
    except ValueError as e:
        logger.error(f"Invalid JSON in webhook request: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        # Return 200 to prevent Telegram from retrying
        # Telegram will retry on non-200 responses
        return {"ok": True, "error": "Update processed with errors"}
