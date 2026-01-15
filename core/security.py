"""
Core Security Module

Provides encryption utilities for sensitive data storage.
"""
import hashlib
import hmac
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from core.config import settings


def get_encryption_key() -> bytes:
    """
    Derive encryption key from SECRET_KEY.
    
    Uses PBKDF2HMAC to derive a Fernet-compatible key from the SECRET_KEY.
    This ensures consistent key generation from the same SECRET_KEY.
    """
    # Use SECRET_KEY as password and a fixed salt (derived from SECRET_KEY)
    # In production, consider using a separate salt stored securely
    salt = hashlib.sha256(settings.SECRET_KEY.encode()).digest()[:16]
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    return key


# Initialize cipher with derived key
_cipher = Fernet(get_encryption_key())


def encrypt_credential(value: str) -> str:
    """
    Encrypt a credential value for secure storage.
    
    Args:
        value: Plain text credential value to encrypt
        
    Returns:
        Encrypted value as base64-encoded string
    """
    encrypted_bytes = _cipher.encrypt(value.encode())
    return encrypted_bytes.decode()


def decrypt_credential(encrypted: str) -> str:
    """
    Decrypt a credential value.
    
    Args:
        encrypted: Encrypted credential value (base64-encoded)
        
    Returns:
        Decrypted plain text value
        
    Raises:
        cryptography.fernet.InvalidToken: If decryption fails
    """
    decrypted_bytes = _cipher.decrypt(encrypted.encode())
    return decrypted_bytes.decode()


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
