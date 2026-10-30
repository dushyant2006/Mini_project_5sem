"""
Client Web Portal Login Handler consuming auth_service.
"""
from auth_service import authenticate_user, create_session_token


def handle_user_login(user_input: str, password_hash: str) -> str:
    """
    Called when a user submits the login form.
    CRITICAL: Calls authenticate_user without the newly required 'mfa_code' parameter!
    """
    is_valid = authenticate_user(username=user_input, password_hash=password_hash)
    if is_valid:
        return create_session_token(user_id=user_input, expiry_hours=12)
    return "LOGIN_FAILED"
