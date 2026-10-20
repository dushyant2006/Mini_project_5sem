"""
Upgraded PaymentLib v2.0.0 (data/new_version)
Contains breaking changes: 'currency' removed, return type changed to Dict, mandatory param added.
"""
from typing import Dict, Any


def process_payment(amount: float) -> Dict[str, Any]:
    """Processes payment. Note: 'currency' removed, return type changed to Dict."""
    return {"status": "success", "amount": amount}


def refund_payment(transaction_id: str, reason: str = "") -> bool:
    """Refunds payment with new optional reason."""
    return True


class PaymentGateway:
    def __init__(self, key: str):
        self.key = key

    def charge(self, amount: float, idempotency_key: str) -> Dict[str, Any]:
        """Breaking change: 'idempotency_key' is now mandatory."""
        return {"status": "success", "amount": amount, "idempotency_key": idempotency_key}
