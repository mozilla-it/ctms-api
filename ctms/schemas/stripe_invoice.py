from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import ComparableBase
from .stripe_price import StripeCurrencyType


class StripeInvoiceStatusEnum(str, Enum):
    """
    Stripe Invoice status values.

    See https://stripe.com/docs/api/invoices/object#invoice_object-status
    """

    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    UNCOLLECTABLE = "uncollectable"
    VOID = "void"


class StripeInvoiceBase(ComparableBase):
    """A Stripe Invoice.

    The subset of fields from a Stripe Invoice record needed for CTMS.
    See https://stripe.com/docs/api/invoices.

    Relations:
    * An Invoice has one Customer
    * An Invoice has one or more Invoice Items
    * An Invoice has zero or one default Payment Method
    """

    stripe_id: Optional[str]
    stripe_created: Optional[datetime]
    stripe_customer_id: Optional[str]
    currency: Optional[StripeCurrencyType]
    total: Optional[int]
    status: Optional[StripeInvoiceStatusEnum]
    default_payment_method_id: Optional[str]
    default_source_id: Optional[str]

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Invoice ID",
                "example": "in_aW52b2ljZQ",
            },
            "stripe_created": {
                "description": "Invoice creation time in Stripe",
                "example": "2021-10-11T19:18:03.350435+00:00",
            },
            "stripe_customer_id": {
                "description": "Stripe Customer ID",
                "example": "cus_Y3VzdG9tZXIx",
            },
            "currency": {
                "description": "Three-letter ISO currency code, in lowercase.",
                "example": "usd",
            },
            "total": {
                "description": "Total after discounts and taxes.",
                "example": 999,
            },
            "status": {
                "description": "The status of the invoice",
                "example": "paid",
            },
            "default_payment_method_id": {
                "description": (
                    "ID of the default payment source for the invoice."
                    " If not set, defaults to the subscription’s default"
                    " source, if any, or to the customer’s default source."
                ),
                "example": "pm_cGF5bWVudF9tZXRob2Q",
            },
            "default_source_id": {
                "description": (
                    "ID of the default payment source for the invoice."
                    " If not set, defaults to the subscription’s default source,"
                    " if any, or to the customer’s default source."
                ),
                "example": "card_ZmFrZSBjYXJk",
            },
        }


class StripeInvoiceCreateSchema(StripeInvoiceBase):
    stripe_id: str
    stripe_created: datetime
    stripe_customer_id: str
    currency: StripeCurrencyType
    total: int
    status: StripeInvoiceStatusEnum
    default_payment_method_id: Optional[str] = None
    default_source_id: Optional[str] = None


StripeInvoiceUpsertSchema = StripeInvoiceCreateSchema


class StripeInvoiceOutputSchema(StripeInvoiceUpsertSchema):
    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
        orm_mode = True
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
