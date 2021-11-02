from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import UUID4, Field

from .base import ComparableBase
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE


class StripeCustomerBase(ComparableBase):
    """
    A Stripe Customer.

    The subset of fields from a Stripe Customer record needed for CTMS.
    See https://stripe.com/docs/api/customers.

    Relations:
    * A Customer (should have) exactly one FxA user. In Stripe, the
      "description" field is used to store the FxA ID, and in this
      database, it is related through the email_id.
    * A Customer has 0 or more Subscriptions
    * A Customer has 0 or 1 default Payment Methods
    * A Customer has 0 or 1 default Sources (Older API, can be viewed as
      Payment Method)
    * A Customer has 0 or more Invoices
    """

    stripe_id: Optional[str]
    stripe_created: Optional[datetime]
    email_id: Optional[UUID4]
    deleted: Optional[bool]
    default_source_id: Optional[str]
    invoice_settings_default_payment_method_id: Optional[str]

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Customer ID",
                "example": "cus_Y3VzdG9tZXI",
            },
            "stripe_created": {
                "description": "Customer creation time in Stripe",
                "example": "2021-10-11T19:18:03.350435+00:00",
            },
            "email_id": {
                "description": EMAIL_ID_DESCRIPTION,
                "example": EMAIL_ID_EXAMPLE,
            },
            "deleted": {
                "description": "Has the customer has been deleted in Stripe?",
                "example": False,
            },
            "default_source_id": {
                "description": "ID of the default payment source for the customer.",
                "example": "card_ZmFrZSBjYXJk",
            },
            "invoice_settings_default_payment_method_id": {
                "description": (
                    "ID of a payment method that’s attached to the customer, to"
                    " be used as the customer’s default payment method for"
                    " subscriptions and invoices."
                ),
                "example": "pm_cGF5bWVudF9tZXRob2Q",
            },
        }


class StripeCustomerCreateSchema(StripeCustomerBase):
    stripe_id: str
    stripe_created: datetime
    email_id: UUID4
    deleted: bool = False


# No changes for upsert
StripeCustomerUpsertSchema = StripeCustomerCreateSchema


class StripeCustomerOutputSchema(StripeCustomerUpsertSchema):
    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
        orm_mode = True
        fields = {
            "create_timestamp": {
                "description": "CTMS Stripe Customer create timestamp.",
                "example": "2021-10-11T19:27:46.440Z",
            },
            "update_timestamp": {
                "description": "CTMS Stripe Customer update timestamp",
                "example": "2021-10-11T19:27:46.440Z",
            },
        }


class StripeCustomerModelSchema(StripeCustomerUpsertSchema):
    class Config:
        extra = "forbid"
