from base64 import b64encode
from typing import Optional


def fake_stripe_id(prefix: str, seed: str, suffix: Optional[str] = None) -> str:
    """Create a fake Stripe ID for testing"""
    body = b64encode(seed.encode()).decode().replace("=", "")
    return f"{prefix}_{body}{suffix if suffix else ''}"
