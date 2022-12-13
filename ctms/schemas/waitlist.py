from datetime import datetime, timezone
from typing import Optional

from pydantic import UUID4, Field, HttpUrl

from .base import ComparableBase
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE


class WaitlistBase(ComparableBase):
    """
    The waitlists schema.

    This is meant to serve as the common and generic schemas to
    all waitlists.

    In this implementation phase, it cohabits with individual (non-generic)
    schemas of Relay and VPN.
    """

    name: str = Field(
        description="Basket slug for the waitlist",
        example="new-product",
    )
    geo: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Waitlist country",
        example="fr",
    )
    source: Optional[HttpUrl] = Field(
        default=None,
        description="Source URL of subscription",
        example="https://www.mozilla.org/en-US/",
    )
    fields: dict = Field(
        default={}, description="Additional fields", example='{"platform": "fr"}'
    )

    class Config:
        orm_mode = True


# No need to change anything, just extend if you want to
WaitlistInSchema = WaitlistBase
WaitlistSchema = WaitlistBase


class UpdatedWaitlistInSchema(WaitlistInSchema):
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Waitlist data update timestamp",
        example="2021-01-28T21:26:57.511Z",
    )


class WaitlistTableSchema(WaitlistBase):
    """
    TODO: figure out how to use this in sync_bq_tables.
    """

    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        example=EMAIL_ID_EXAMPLE,
    )
    create_timestamp: datetime = Field(
        description="Waitlist data creation timestamp",
        example="2020-12-05T19:21:50.908000+00:00",
    )
    update_timestamp: datetime = Field(
        description="Waitlist data update timestamp",
        example="2021-02-04T15:36:57.511000+00:00",
    )

    class Config:
        extra = "forbid"


class RelayWaitlistBase(ComparableBase):
    """
    The Mozilla Relay Waitlist schema.

    """

    geo: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Relay waitlist country",
        example="fr",
    )

    class Config:
        orm_mode = True


# No need to change anything, just extend if you want to
RelayWaitlistInSchema = RelayWaitlistBase
RelayWaitlistSchema = RelayWaitlistBase


class UpdatedRelayWaitlistInSchema(RelayWaitlistInSchema):
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Relay Waitlist data update timestamp",
        example="2021-01-28T21:26:57.511Z",
    )


class RelayWaitlistTableSchema(RelayWaitlistBase):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        example=EMAIL_ID_EXAMPLE,
    )
    create_timestamp: datetime = Field(
        description="Relay Waitlist data creation timestamp",
        example="2020-12-05T19:21:50.908000+00:00",
    )
    update_timestamp: datetime = Field(
        description="Relay Waitlist data update timestamp",
        example="2021-02-04T15:36:57.511000+00:00",
    )

    class Config:
        extra = "forbid"


class VpnWaitlistBase(ComparableBase):
    """
    The Mozilla VPN Waitlist schema.

    This was previously the Firefox Private Network (fpn) waitlist data,
    with a similar purpose.
    """

    geo: Optional[str] = Field(
        default=None,
        max_length=100,
        description="VPN waitlist country, FPN_Waitlist_Geo__c in Salesforce",
        example="fr",
    )
    platform: Optional[str] = Field(
        default=None,
        max_length=100,
        description=(
            "VPN waitlist platforms as comma-separated list,"
            " FPN_Waitlist_Platform__c in Salesforce"
        ),
        example="ios,mac",
    )

    class Config:
        orm_mode = True


# No need to change anything, just extend if you want to
VpnWaitlistInSchema = VpnWaitlistBase
VpnWaitlistSchema = VpnWaitlistBase


class UpdatedVpnWaitlistInSchema(VpnWaitlistInSchema):
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="VPN Waitlist data update timestamp",
        example="2021-01-28T21:26:57.511Z",
    )


class VpnWaitlistTableSchema(VpnWaitlistBase):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        example=EMAIL_ID_EXAMPLE,
    )
    create_timestamp: datetime = Field(
        description="VPN Waitlist data creation timestamp",
        example="2020-12-05T19:21:50.908000+00:00",
    )
    update_timestamp: datetime = Field(
        description="VPN Waitlist data update timestamp",
        example="2021-02-04T15:36:57.511000+00:00",
    )

    class Config:
        extra = "forbid"
