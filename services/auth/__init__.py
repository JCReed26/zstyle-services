"""
Authentication Service

Handles all credential retrieval and token management.
Agents NEVER import this directly - only agent wrappers use it.
"""
from .auth_service import AuthService

__all__ = ["AuthService"]

