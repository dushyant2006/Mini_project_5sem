"""
Client Alerting Dispatcher calling notification_service.
"""
from notification_service import send_email


def notify_admin_of_error(error_log: str) -> bool:
    """CRITICAL: Calls send_email which was deleted in v2!"""
    return send_email(
        to_address="admin@company.com",
        subject="High Severity Production Alert",
        body=error_log
    )
