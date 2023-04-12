from base64 import b64encode
from typing import Optional


def fake_stripe_id(prefix: str, seed: str, suffix: Optional[str] = None) -> str:
    """Create a fake Stripe ID for testing"""
    body = b64encode(seed.encode()).decode().replace("=", "")
    return f"{prefix}_{body}{suffix if suffix else ''}"


# Documentation and test Stripe IDs
FAKE_STRIPE_ID = {
    "Customer": fake_stripe_id("cus", "customer"),
    "Invoice": fake_stripe_id("in", "invoice"),
    "(Invoice) Line Item": fake_stripe_id("il", "invoice line item"),
    "Payment Method": fake_stripe_id("pm", "payment_method"),
    "Price": fake_stripe_id("price", "price"),
    "Product": fake_stripe_id("prod", "product"),
    "Subscription": fake_stripe_id("sub", "subscription"),
    "Subscription Item": fake_stripe_id("si", "subscription_item"),
}
