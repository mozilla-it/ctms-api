from base64 import b64encode
from datetime import datetime, timezone
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

# Sample data to pass to Stripe[Object]CreateSchema
SAMPLE_STRIPE_DATA = {
    "Customer": {
        "stripe_id": FAKE_STRIPE_ID["Customer"],
        "stripe_created": datetime(2021, 10, 25, 15, 34, tzinfo=timezone.utc),
        # TODO magic string from fxa schema
        "fxa_id": "6eb6ed6ac3b64259968aa490c6c0b9df",
        "default_source_id": None,
        "invoice_settings_default_payment_method_id": FAKE_STRIPE_ID["Payment Method"],
    },
    "Subscription": {
        "stripe_id": FAKE_STRIPE_ID["Subscription"],
        "stripe_created": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "stripe_customer_id": FAKE_STRIPE_ID["Customer"],
        "default_source_id": None,
        "default_payment_method_id": None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "current_period_start": datetime(2021, 10, 27, tzinfo=timezone.utc),
        "current_period_end": datetime(2021, 11, 27, tzinfo=timezone.utc),
        "ended_at": None,
        "start_date": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "status": "active",
    },
    "SubscriptionItem": {
        "stripe_id": FAKE_STRIPE_ID["Subscription Item"],
        "stripe_created": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "stripe_subscription_id": FAKE_STRIPE_ID["Subscription"],
        "stripe_price_id": FAKE_STRIPE_ID["Price"],
    },
    "Price": {
        "stripe_id": FAKE_STRIPE_ID["Price"],
        "stripe_created": datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc),
        "stripe_product_id": FAKE_STRIPE_ID["Product"],
        "active": True,
        "currency": "usd",
        "recurring_interval": "month",
        "recurring_interval_count": 1,
        "unit_amount": 999,
    },
    "Invoice": {
        "stripe_id": FAKE_STRIPE_ID["Invoice"],
        "stripe_created": datetime(2021, 10, 28, tzinfo=timezone.utc),
        "stripe_customer_id": FAKE_STRIPE_ID["Customer"],
        "default_source_id": None,
        "default_payment_method_id": None,
        "currency": "usd",
        "total": 1000,
        "status": "open",
    },
    "InvoiceLineItem": {
        "stripe_id": FAKE_STRIPE_ID["(Invoice) Line Item"],
        "stripe_price_id": FAKE_STRIPE_ID["Price"],
        "stripe_invoice_id": FAKE_STRIPE_ID["Invoice"],
        "stripe_subscription_id": FAKE_STRIPE_ID["Subscription"],
        "stripe_subscription_item_id": FAKE_STRIPE_ID["Subscription Item"],
        "stripe_type": "subscription",
        "amount": 1000,
        "currency": "usd",
    },
}
