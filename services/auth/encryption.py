"""
Token Encryption Module

Provides encryption/decryption for OAuth tokens stored in the database.
Uses Fernet symmetric encryption from cryptography library.
"""
import os
import base64
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """Get encryption key from Secret Manager or env."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        # Try Secret Manager
        try:
            from database.core import _get_secret_from_gcp
            key = _get_secret_from_gcp("ENCRYPTION_KEY")
        except Exception:
            pass
    
    if key:
        try:
            return base64.urlsafe_b64decode(key)
        except Exception:
            # If decoding fails, treat as raw key
            return key.encode() if isinstance(key, str) else key
    else:
        # Generate and log warning (should be set in production)
        logger.warning("ENCRYPTION_KEY not set - tokens stored unencrypted")
        return Fernet.generate_key()


# Initialize cipher with key
_cipher = None

def _get_cipher():
    """Lazy initialization of cipher."""
    global _cipher
    if _cipher is None:
        try:
            key = get_encryption_key()
            _cipher = Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption cipher: {e}")
            # Return None to disable encryption
            return None
    return _cipher


def encrypt_token(token: str) -> str:
    """
    Encrypt token for storage.
    
    Args:
        token: Plain text token to encrypt
        
    Returns:
        Encrypted token string, or original token if encryption fails
    """
    if not token:
        return token
    
    cipher = _get_cipher()
    if not cipher:
        logger.warning("Encryption not available - storing token unencrypted")
        return token
    
    try:
        return cipher.encrypt(token.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt token: {e}")
        return token


def decrypt_token(encrypted: str) -> str:
    """
    Decrypt token from storage.
    
    Args:
        encrypted: Encrypted token string
        
    Returns:
        Decrypted token string, or original string if decryption fails
    """
    if not encrypted:
        return encrypted
    
    cipher = _get_cipher()
    if not cipher:
        # Assume unencrypted if cipher not available
        return encrypted
    
    try:
        return cipher.decrypt(encrypted.encode()).decode()
    except Exception as e:
        # If decryption fails, might be unencrypted (backward compatibility)
        logger.debug(f"Failed to decrypt token (may be unencrypted): {e}")
        return encrypted

