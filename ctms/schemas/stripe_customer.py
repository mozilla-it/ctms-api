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
    * A Customer has 0 or more Invoices
    """

    stripe_id: Optional[str] = None
    stripe_created: Optional[datetime] = None
    invoice_settings_default_payment_method: Optional[str] = None

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Customer ID",
                "example": "cus_8epDebVEl8Bs2V",
            },
            "stripe_created": {
                "description": "Customer creation time in Stripe",
                "example": "2021-10-11T19:18:03.350435+00:00",
            },
            "invoice_settings_default_payment_method": {
                "description": "Default payment method for the Customer.",
                "example": "pm_1JmPBfKb9q6OnNsLlzx8GamM",
            },
        }


class StripeCustomerCreateSchema(StripeCustomerBase):
    stripe_id: str
    stripe_created: datetime


# No changes for upsert
StripeCustomerUpsertSchema = StripeCustomerCreateSchema


class StripeCustomerOutputSchema(StripeCustomerUpsertSchema):
    invoice_settings_default_payment_method: Optional[str]
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


class StripeCustomerModelSchema(StripeCustomerOutputSchema):

    email_id: UUID4

    class Config:
        extra = "forbid"
        fields = {
            "email_id": {
                "description": EMAIL_ID_DESCRIPTION,
                "example": EMAIL_ID_EXAMPLE,
            }
        }
