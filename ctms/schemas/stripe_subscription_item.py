from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripeSubscriptionItemBase(ComparableBase):
    """
    A Stripe Subscription Item.

    The subset of fields from a Stripe Subscription Item record needed for
    CTMS. See https://stripe.com/docs/api/subscription_items.

    Relations:
    * A Subscription Item has one Subscription
    * A Subscription Item has one Price
    """

    stripe_id: Optional[str]
    stripe_created: Optional[datetime]
    stripe_subscription_id: Optional[str]
    stripe_price_id: Optional[str]

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Subscription Item ID",
                "example": "si_c3Vic2NyaXB0aW9uX2l0ZW0",
            },
            "stripe_created": {
                "description": "Subscription creation time in Stripe.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "stripe_subscription_id": {
                "description": "Stripe Subscription ID",
                "example": "sub_c3Vic2NyaXB0aW9u",
            },
            "stripe_price_id": {
                "description": "Stripe Price ID",
                "example": "price_cHJpY2U",
            },
        }


class StripeSubscriptionItemCreateSchema(StripeSubscriptionItemBase):
    stripe_id: str
    stripe_created: datetime
    stripe_subscription_id: str
    stripe_price_id: str


StripeSubscriptionItemUpsertSchema = StripeSubscriptionItemCreateSchema


class StripeSubscriptionItemOutputSchema(StripeSubscriptionItemUpsertSchema):
    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
        orm_mode = True
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


class StripeSubscriptionItemModelSchema(StripeSubscriptionItemOutputSchema):
    class Config:
        extra = "forbid"
