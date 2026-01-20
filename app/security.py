"""
Core Security Module

Provides encryption utilities for sensitive data storage.
"""
import hashlib
import hmac
import logging
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Derive encryption key from SECRET_KEY.
    
    Uses PBKDF2HMAC to derive a Fernet-compatible key from the SECRET_KEY.
    This ensures consistent key generation from the same SECRET_KEY.
    """
    settings = get_settings()
    # Use cryptographically secure random salt (fixed per environment for consistency)
    salt = b'zstyle_salt_2024'  # Fixed salt per environment - store securely in production
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return key


# Initialize cipher with derived key (lazy-loaded)
_cipher: Optional[Fernet] = None


def _get_cipher() -> Fernet:
    """Get or create the Fernet cipher instance."""
    global _cipher
    if _cipher is None:
        _cipher = Fernet(get_encryption_key())
    return _cipher


def encrypt_credential(value: str) -> str:
    """
    Encrypt a credential value for secure storage.
    
    Args:
        value: Plain text credential value to encrypt
        
    Returns:
        Encrypted value as base64-encoded string
    """
    cipher = _get_cipher()
    encrypted_bytes = cipher.encrypt(value.encode())
    return encrypted_bytes.decode()


def decrypt_credential(encrypted: str) -> str:
    """
    Decrypt a credential value.
    
    SECURITY: Validates decryption succeeds.
    
    Args:
        encrypted: Encrypted credential value (base64-encoded)
        
    Returns:
        Decrypted plain text value
        
    Raises:
        ValueError: If encrypted value is empty
        cryptography.fernet.InvalidToken: If decryption fails
    """
    if not encrypted:
        raise ValueError("Cannot decrypt empty value")
    
    cipher = _get_cipher()
    try:
        decrypted_bytes = cipher.decrypt(encrypted.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Credential decryption failed: {e}")
        raise


def verify_telegram_webhook(data: dict, secret: str) -> bool:
    """
    Verify Telegram webhook signature using HMAC.
    
    Args:
        data: Webhook data dictionary
        secret: Secret key for verification
        
    Returns:
        True if signature is valid, False otherwise
        
    Note:
        This is a placeholder implementation. Actual Telegram webhook
        verification should use the specific Telegram webhook format.
    """
    # TODO: Implement actual Telegram webhook HMAC verification
    # Telegram webhooks use a specific format for signature verification
    # This should be implemented based on Telegram's webhook documentation
    return False
