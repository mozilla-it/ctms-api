from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class StripeProductBase(ComparableBase):
    """
    A Stripe Product.

    The subset of fields from a Stripe Product record needed for CTMS.
    See https://stripe.com/docs/api/products

    Relations:
    * A Product has 0 or more Prices
    """

    stripe_id: Optional[str]
    stripe_created: Optional[datetime]
    stripe_updated: Optional[datetime]
    name: Optional[str]
    acoustic_name: Optional[str]

    class Config:
        fields = {
            "stripe_id": {
                "description": "Stripe Product ID",
                "example": "prod_KPReWHqwGqZBzc",
            },
            "stripe_created": {
                "description": "Product creation time in Stripe.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "stripe_updated": {
                "description": "Product update time in Stripe.",
                "example": "2021-10-14T18:33:09.348050+00:00",
            },
            "name": {
                "description": "The product’s name, meant to be displayable to the customer.",
                "example": "Staging Managed Hubs",
            },
            "acoustic_name": {
                "description": "Product name as synced to Acoustic.",
                "example": "Hubs"
            },
        }


class StripeProductCreateSchema(StripeProductBase):
    stripe_id: str
    stripe_created: datetime
    stripe_updated: datetime
    name: str


StripeProductUpsertSchema = StripeProductCreateSchema


class StripeProductOutputSchema(StripeProductUpsertSchema):
    orm_mode = True

    acoustic_name: str
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


class StripeProductModelSchema(StripeProductOutputSchema):
    class Config:
        extra = "forbid"
