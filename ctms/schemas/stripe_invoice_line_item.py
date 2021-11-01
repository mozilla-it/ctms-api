from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripeInvoiceLineTypeEnum(str, Enum):
    """
    Stripe Invoice Line type values.

    See https://stripe.com/docs/api/invoices/line_item#invoice_line_item_object-type
    """

    INVOICEITEM = "invoiceitem"
    SUBSCRIPTION = "subscription"


class StripeInvoiceLineItemBase(ComparableBase):
    """
    A Stripe Invoice Line Item.

    The subset of fields from a Stripe Invoice Line Item record needed for
    CTMS. https://stripe.com/docs/api/invoices/line_item.

    This is not the same as Invoice Items, which are items added to a user's
    next invoice.

    Relations:
    * An Invoice Line Item has one Invoice (Stripe does not track, we do)
    * An Invoice Line Item has 0 or 1 Invoice Items (ID tracked, not object)
    * An Invoice Line Item has 0 or 1 Subscriptions
    * An Invoice Line Item has 0 or 1 Subscription Items
    * An Invoice Line Item has one Price
    """

    stripe_id: Optional[str]
    stripe_invoice_id: Optional[str]
    stripe_type: Optional[StripeInvoiceLineTypeEnum]
    stripe_price_id: Optional[str]
    stripe_invoice_item_id: Optional[str]
    stripe_subscription_id: Optional[str]
    stripe_subscription_item_id: Optional[str]
    amount: Optional[int]
    currency: Optional[str]

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Invoice Line Item ID",
                "example": "il_aW52b2ljZSBsaW5lIGl0ZW0",
            },
            "stripe_invoice_id": {
                "description": "Stripe Invoice ID",
                "example": "in_aW52b2ljZQ",
            },
            "stripe_type": {
                "description": (
                    "A string identifying the type of the source of this line" " item"
                ),
                "example": "subscription",
            },
            "stripe_price_id": {
                "description": "Stripe Price ID",
                "example": "price_cHJpY2U",
            },
            "stripe_invoice_item_id": {
                "description": (
                    "The ID of the invoice item associated with this line item"
                    " if any"
                ),
                "example": "ii_aW52b2ljZSBpdGVtCg",
            },
            "stripe_subscription_id": {
                "description": (
                    "The subscription that the invoice item pertains to, if any"
                ),
                "example": "sub_c3Vic2NyaXB0aW9u",
            },
            "stripe_subscription_item_id": {
                "description": (
                    "The subscription item that generated this invoice item."
                    " Left empty if the line item is not an explicit result of a"
                    " subscription."
                ),
                "example": "si_c3Vic2NyaXB0aW9uX2l0ZW0",
            },
            "amount": {
                "description": "The amount, in cents",
                "example": -57,
            },
            "currency": {
                "description": "Three-letter ISO currency code, in lowercase",
                "example": "usd",
            },
        }


class StripeInvoiceLineItemCreateSchema(StripeInvoiceLineItemBase):
    stripe_id: str
    stripe_invoice_id: str
    stripe_type: StripeInvoiceLineTypeEnum
    stripe_price_id: str
    stripe_invoice_item_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_subscription_item_id: Optional[str] = None
    amount: int
    currency: str


StripeInvoiceLineItemUpsertSchema = StripeInvoiceLineItemCreateSchema


class StripeInvoiceLineItemOutputSchema(StripeInvoiceLineItemUpsertSchema):
    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
        orm_mode = True
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


class StripeInvoiceLineItemModelSchema(StripeInvoiceLineItemOutputSchema):
    class Config:
        extra = "forbid"
