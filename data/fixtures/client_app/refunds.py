"""
Client Refunds and Customer Service Worker consuming payment_gateway.
"""
from payment_gateway import refund_transaction


def issue_refund(order_id: str, reason: str = "item_returned") -> bool:
    """Issues order refund back to customer."""
    print(f"Issuing refund for order {order_id}...")
    # Safe call - 'manager_approval' has default in v2
    return refund_transaction(tx_id=order_id, reason=reason)
