"""
PaymentGateway Library Version 2.0.0 (Upgraded Version with Breaking Changes)
"""
from typing import Optional, Dict, Any


def process_payment(amount: float, timeout: int = 30) -> Dict[str, Any]:
    """
    Processes a card payment.
    BREAKING CHANGE 1: 'currency' parameter was removed!
    BREAKING CHANGE 2: Return type changed from bool to Dict[str, Any]!
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    return {"status": "success", "amount": amount}


def refund_transaction(tx_id: str, reason: str = "", manager_approval: bool = True) -> bool:
    """
    Refunds a previously completed transaction.
    COMPATIBLE: 'manager_approval' added with a default value.
    """
    return True


def unused_analytics_event(name: str, payload: Dict[str, Any]) -> None:
    """
    BREAKING CHANGE 3: Added mandatory 'payload' parameter.
    UNREACHABLE: No client call-sites invoke this!
    """
    pass


class StripeGateway:
    """
    Gateway provider for Stripe.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key

    def charge(self, token: str, amount: int, idempotency_key: str) -> Dict[str, Any]:
        """
        BREAKING CHANGE 4: Added mandatory 'idempotency_key' parameter!
        """
        return {"status": "succeeded", "token": token, "amount": amount, "idempotency_key": idempotency_key}

    def cancel(self, charge_id: str) -> None:
        pass

    def get_balance(self) -> float:
        """
        COMPATIBLE: Added new method.
        """
        return 10000.0
