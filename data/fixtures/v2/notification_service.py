"""
Notifications & Email Service v2.0.0 (Breaking Function Removal)
"""
from typing import List, Optional

# BREAKING: send_email() was completely DELETED and replaced with send_templated_message()!

def send_templated_message(recipient_id: str, template_key: str, context: dict) -> bool:
    """New notification mechanism."""
    return True


def broadcast_announcement(message: str) -> int:
    """Broadcasts notification to all registered users."""
    return 150
