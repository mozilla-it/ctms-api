from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripeSubscriptionStatusEnum(str, Enum):
    """
    Stripe Subscription status values.

    See https://stripe.com/docs/api/subscriptions/object#subscription_object-status
    """

    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class StripeSubscriptionBase(ComparableBase):
    """
    A Stripe Subscription.

    The subset of fields from a Stripe Subscription record needed for CTMS.
    See https://stripe.com/docs/api/subscriptions.

    Relations:
    * A Subscription has one Customer
    * A Subscription has one or more Subscription Items. For Mozilla in 2021,
      it is currently 0 or 1, but we may use bundles in the future.
    * A Subscription has 0 or 1 default Payment Methods
    * A Subscription has 0 or 1 latest Invoices
    """

    stripe_id: Optional[str]
    stripe_created: Optional[datetime]
    cancel_at_period_end: Optional[bool]
    canceled_at: Optional[datetime]
    current_period_end: Optional[datetime]
    current_period_start: Optional[datetime]
    ended_at: Optional[datetime]
    start_date: Optional[datetime]
    status: Optional[StripeSubscriptionStatusEnum]
    default_payment_method: Optional[str]

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Subscription ID",
                "example": "sub_CUcvxLlcRGBsAT",
            },
            "stripe_created": {
                "description": "Subscription creation time in Stripe.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "cancel_at_period_end": {
                "description": (
                    "True if the subscription will be canceled at the end of"
                    " the current period"
                ),
                "example": False,
            },
            "canceled_at": {
                "description": (
                    "If the subscription has been canceled, the date of that"
                    " cancellation."
                ),
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "current_period_end": {
                "description": (
                    "End of the current period that the subscription has been"
                    " invoiced for. At the end of this period, a new invoice will"
                    " be created."
                ),
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "current_period_start": {
                "description": (
                    "Start of the current period that the subscription has been"
                    " invoiced for."
                ),
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "ended_at": {
                "description": (
                    "If the subscription has ended, the date the subscription" " ended."
                ),
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "start_date": {
                "description": "Date when the subscription was first created.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "status": {"description": "Subscription status", "example": "active"},
            "default_payment_method": {
                "description": (
                    "ID of the default payment method for the"
                    " subscription. If unset, invoices will use the"
                    " customer’s invoice_settings.default_payment_method"
                ),
                "example": "",
            },
        }


class StripeSubscriptionCreateSchema(StripeSubscriptionBase):
    stripe_id: str
    stripe_created: datetime
    cancel_at_period_end: bool
    canceled_at: datetime
    current_period_end: datetime
    current_period_start: datetime
    ended_at: datetime
    start_date: datetime
    status: StripeSubscriptionStatusEnum
    default_payment_method: Optional[str] = None


StripeSubscriptionUpsertSchema = StripeSubscriptionCreateSchema


class StripeSubscriptionOutputSchema(StripeSubscriptionUpsertSchema):
    orm_mode = True

    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
        fields = {
            "create_timestamp": {
                "description": "CTMS create timestamp.",
                "example": "2021-10-11T19:27:46.440Z",
            },
            "update_timestamp": {
                "description": "CTMS update timestamp",
                "example": "2021-10-11T19:27:46.440Z",
            },
        }


class StripeSubscriptionModelSchema(StripeSubscriptionOutputSchema):
    stripe_customer_id: str

    class Config:
        extra = "forbid"
        fields = {
            "stripe_customer_id": {
                "description": "Stripe Customer ID",
                "example": "cus_8epDebVEl8Bs2V",
            },
        }
