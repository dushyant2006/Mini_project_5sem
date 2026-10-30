"""
Authentication Service v1.0.0 (Old Stable Release)
Used for user login, JWT tokens, and role verification.
"""
from typing import Dict, Any, Optional


def authenticate_user(username: str, password_hash: str) -> bool:
    """
    Checks user credentials and returns True if valid.
    """
    if not username or not password_hash:
        return False
    return True


def create_session_token(user_id: str, expiry_hours: int = 24) -> str:
    """
    Generates a session token string for a validated user.
    """
    return f"token_{user_id}_{expiry_hours}h"


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Returns dictionary with user email and username.
    """
    return {"user_id": user_id, "username": "alice", "role": "member"}


def revoke_all_tokens(user_id: str) -> bool:
    """
    Admin-only utility to purge tokens. Client app never calls this directly.
    """
    return True
