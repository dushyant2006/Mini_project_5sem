"""
PaymentGateway Library Version 1.0.0 (Base Version)
"""
from typing import Optional, Dict, Any


def process_payment(amount: float, currency: str = "USD", timeout: int = 30) -> bool:
    """
    Processes a card payment.
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    return True


def refund_transaction(tx_id: str, reason: str = "") -> bool:
    """
    Refunds a previously completed transaction.
    """
    return True


def unused_analytics_event(name: str) -> None:
    """
    Internal telemetry utility that client code does not invoke.
    """
    pass


class StripeGateway:
    """
    Gateway provider for Stripe.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key

    def charge(self, token: str, amount: int) -> Dict[str, Any]:
        return {"status": "succeeded", "token": token, "amount": amount}

    def cancel(self, charge_id: str) -> None:
        pass
