"""
Client E-Commerce Checkout Service consuming payment_gateway.
"""
from payment_gateway import process_payment, StripeGateway


def run_checkout(customer_id: str, cart_total: float) -> bool:
    """Executes customer purchase transaction."""
    print(f"Checking out customer {customer_id}...")

    # Actively passes 'currency' which will break in v2!
    success = process_payment(amount=cart_total, currency="USD")

    # Uses StripeGateway
    gateway = StripeGateway(api_key="sk_test_12345")
    res = gateway.charge(token="tok_visa", amount=int(cart_total * 100))
    return success and res.get("status") == "succeeded"
