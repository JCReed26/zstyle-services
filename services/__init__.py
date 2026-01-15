"""
ZStyle Services Package

Core services for the ZStyle system.

Available Services:
    - memory_service: User memory management (Memory-First Architecture)
    - activity_log_service: User activity logging and export
    - credential_service: Secure credential storage and retrieval
"""
from .memory.memory_service import memory_service
from .activity_log import activity_log_service
from .credential_service import CredentialService

credential_service = CredentialService()

__all__ = [
    "memory_service",
    "activity_log_service",
    "credential_service",
]
