from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripeInvoiceBase(ComparableBase):
    """A Stripe Invoice."""

    currency: Optional[str]
    stripe_created: Optional[datetime]
    total: Optional[int]
    status: Optional[str]

    payment_type: Optional[str]
    payment_card_brand: Optional[str]
    payment_card_last4: Optional[str]


StripeInvoiceCreateSchema = StripeInvoiceBase
StripeInvoiceUpsertSchema = StripeInvoiceCreateSchema


class StripeInvoiceOutputSchema(StripeInvoiceUpsertSchema):
    orm_mode = True

    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
        fields = {
            "create_timestamp": {
                "description": "CTMS Stripe Invoice create timestamp.",
                "example": "2021-10-11T19:27:46.440Z",
            },
            "update_timestamp": {
                "description": "CTMS Stripe Invoice update timestamp",
                "example": "2021-10-11T19:27:46.440Z",
            },
        }


class StripeInvoiceModelSchema(StripeInvoiceOutputSchema):
    class Config:
        extra = "forbid"
