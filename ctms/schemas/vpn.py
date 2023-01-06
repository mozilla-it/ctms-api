from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


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
