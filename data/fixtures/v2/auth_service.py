"""
Authentication Service v2.0.0 (New Release with Breaking Changes)
"""
from typing import Dict, Any, Optional


def authenticate_user(username: str, password_hash: str, mfa_code: str) -> Dict[str, Any]:
    """
    BREAKING CHANGE 1: Mandatory 'mfa_code' parameter added! (Old callers without mfa_code will fail)
    BREAKING CHANGE 2: Return type changed from bool to Dict ({"status": "ok", "token": "..."})
    """
    return {"status": "ok", "username": username, "authenticated": True}


def create_session_token(user_id: str, expiry_hours: int = 24, device_info: str = "web") -> str:
    """
    COMPATIBLE CHANGE: 'device_info' added with default value.
    """
    return f"token_{user_id}_{expiry_hours}h_{device_info}"


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    COMPATIBLE: Unchanged signature.
    """
    return {"user_id": user_id, "username": "alice", "role": "member"}


def revoke_all_tokens(user_id: str, reason: str) -> bool:
    """
    BREAKING CHANGE 3: Mandatory 'reason' parameter added.
    UNREACHABLE: No caller invokes this in the client app!
    """
    return True
