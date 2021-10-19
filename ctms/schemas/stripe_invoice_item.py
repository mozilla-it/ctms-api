from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripeInvoiceItemBase(ComparableBase):
    """
    A Stripe Invoice Item.

    The subset of fields from a Stripe Invoice Item record needed for
    CTMS. See https://stripe.com/docs/api/invoiceitems.

    Relations:
    * An Invoice Item has one Invoice
    * An Invoice Item has one Customer (we track through Invoice)
    * An Invoice Item has one Subscription Item (we don't track)
    * An Invoice Item has one Subscription (we don't track)
    * An Invoice Item has one Price
    """

    stripe_id: Optional[str]
    stripe_created: Optional[datetime]

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Invoice Item ID",
                "example": "il_1JmPBbKb9q6OnNsLyp5I8Sd2",
            },
            "stripe_created": {
                "description": "Invoice Item creation time in Stripe",
                "example": "2021-10-11T19:18:03.350435+00:00",
            },
        }


class StripeInvoiceItemCreateSchema(StripeInvoiceItemBase):
    stripe_id: str
    stripe_created: datetime


StripeInvoiceItemUpsertSchema = StripeInvoiceItemCreateSchema


class StripeInvoiceItemOutputSchema(StripeInvoiceItemUpsertSchema):
    orm_mode = True

    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
        fields = {
            "create_timestamp": {
                "description": "CTMS Stripe Invoice Item create timestamp.",
                "example": "2021-10-11T19:27:46.440Z",
            },
            "update_timestamp": {
                "description": "CTMS Stripe Invoice Item update timestamp",
                "example": "2021-10-11T19:27:46.440Z",
            },
        }


class StripeInvoiceItemModelSchema(StripeInvoiceItemOutputSchema):
    stripe_invoice_id = str
    stripe_price_id = str

    class Config:
        extra = "forbid"
        fields = {
            "stripe_invoice_id": {
                "description": "Stripe Invoice ID",
                "example": "in_1JfEslKb9q6OnNsLfesYunhQ",
            },
            "stripe_price_id": {
                "description": "Stripe Price ID",
                "example": "plan_FvPMH5lVx1vhV0",
            },
        }
