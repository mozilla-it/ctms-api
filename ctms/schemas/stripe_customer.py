from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripeCustomerBase(ComparableBase):
    """A Stripe Customer."""

    customer_id: Optional[str] = None
    customer_created: Optional[datetime] = None

    class Config:
        fields = {
            "customer_id": {
                "description": "Stripe customer ID",
                "example": "cus_8epDebVEl8Bs2V",
            },
            "customer_created": {
                "description": "Customer creation time (in Stripe)",
                "example": "2021-10-11T19:18:03.350435+00:00",
            },
        }


class StripeCustomerCreateSchema(StripeCustomerBase):

    customer_id: str


# No changes for upsert
StripeCustomerUpsertSchema = StripeCustomerCreateSchema


class StripeCustomerOutputSchema(StripeCustomerUpsertSchema):
    customer_created: datetime

    orm_mode = True
    create_timestamp: datetime
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    class Config:
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
    class Config:
        extra = "forbid"
