from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import ConstrainedStr, Field

from .base import ComparableBase


class StripePriceIntervalEnum(str, Enum):
    """
    Stripe Price recurring interval values.

    See https://stripe.com/docs/api/prices/object#price_object-recurring-interval
    """

    DAY = "day"
    MONTH = "month"
    WEEK = "week"
    YEAR = "year"


class StripeCurrencyType(ConstrainedStr):
    to_lower = True
    min_length = 3
    max_length = 3


class StripePriceBase(ComparableBase):
    """
    A Stripe Price.

    The subset of fields from a Stripe Price record needed for CTMS.
    See https://stripe.com/docs/api/prices.

    Relations:
    * A Price has one Product
    """

    stripe_id: Optional[str]
    stripe_created: Optional[datetime]
    stripe_product_id: Optional[str]
    active: Optional[bool]
    currency: Optional[StripeCurrencyType]
    recurring_interval: Optional[StripePriceIntervalEnum]
    recurring_interval_count: Optional[int]
    unit_amount: Optional[int]

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Price ID",
                "example": "price_cHJpY2U",
            },
            "stripe_created": {
                "description": "Price creation time in Stripe.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "stripe_product_id": {
                "description": "Stripe Product ID",
                "example": "prod_cHJvZHVjdA",
            },
            "active": {
                "description": "Whether the price can be used for new purchases",
                "example": True,
            },
            "currency": {
                "description": "Three-letter ISO currency code, in lowercase.",
                "example": "usd",
            },
            "recurring_interval": {
                "description": (
                    "The frequency at which a subscription is billed."
                    " None if type=one_time."
                ),
                "example": "month",
            },
            "recurring_interval_count": {
                "description": (
                    "The number of intervals between subscription billings."
                    " None if type=one_time."
                ),
                "example": 1,
            },
            "unit_amount": {
                "description": (
                    "A positive integer in cents (or 0 for a free price)"
                    " representing how much to charge."
                    " None if billing_scheme=tiered."
                ),
                "example": 999,
            },
        }


class StripePriceCreateSchema(StripePriceBase):
    stripe_id: str
    stripe_created: datetime
    stripe_product_id: str
    active: bool = True
    currency: StripeCurrencyType


StripePriceUpsertSchema = StripePriceCreateSchema


class StripePriceOutputSchema(StripePriceUpsertSchema):
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


class StripePriceModelSchema(StripePriceOutputSchema):
    class Config:
        extra = "forbid"
