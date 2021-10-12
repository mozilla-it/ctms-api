from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripeSubscriptionBase(ComparableBase):
    """A Stripe Subscription."""

    cancel_at: Optional[datetime]
    cancel_at_period_end: Optional[bool]
    canceled_at: Optional[datetime]
    stripe_created: Optional[datetime]
    current_period_end: Optional[datetime]
    current_period_start: Optional[datetime]
    ended_at: Optional[datetime]
    price_amount: Optional[int]
    price_currency: Optional[str]
    price_interval: Optional[str]
    price_interval_count: Optional[int]
    start_date: Optional[datetime]
    status: Optional[str]


StripeSubscriptionCreateSchema = StripeSubscriptionBase
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
                "description": "CTMS Stripe Subscription create timestamp.",
                "example": "2021-10-11T19:27:46.440Z",
            },
            "update_timestamp": {
                "description": "CTMS Stripe Subscription update timestamp",
                "example": "2021-10-11T19:27:46.440Z",
            },
        }


class StripeSubscriptionModelSchema(StripeSubscriptionOutputSchema):
    class Config:
        extra = "forbid"
