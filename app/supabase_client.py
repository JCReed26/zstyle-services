"""
Supabase Client Helper

Provides Supabase client initialization for authentication and database operations.
"""
from supabase import create_client, Client
from app.config import settings


def get_supabase_client(use_service_role: bool = False) -> Client:
    """
    Get Supabase client instance.
    
    Args:
        use_service_role: If True, use service role key (bypasses RLS).
                         If False, use anonymous key (respects RLS).
    
    Returns:
        Supabase client instance
    """
    if use_service_role:
        key = settings.SUPABASE_SERVICE_ROLE_KEY
    else:
        key = settings.SUPABASE_ANON_KEY
    
    return create_client(settings.SUPABASE_URL, key)
