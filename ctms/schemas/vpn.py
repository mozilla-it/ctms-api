from typing import Optional

from pydantic import UUID4, EmailStr, Field, HttpUrl

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
