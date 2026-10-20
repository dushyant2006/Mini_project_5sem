"""
Legacy PaymentLib v1.0.0 (data/old_version)
"""
from typing import Dict, Any


def process_payment(amount: float, currency: str = "USD") -> bool:
    """Processes payment with currency parameter."""
    return amount > 0


def refund_payment(transaction_id: str) -> bool:
    """Refunds payment by transaction ID."""
    return True


class PaymentGateway:
    def __init__(self, key: str):
        self.key = key

    def charge(self, amount: float) -> Dict[str, Any]:
        return {"status": "success", "amount": amount}
