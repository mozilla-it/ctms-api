from __future__ import annotations

from pydantic import UUID4, ConfigDict, Field, model_validator

from .base import ComparableBase
from .common import AnyUrlString, ZeroOffsetDatetime
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE


class WaitlistBase(ComparableBase):
    """
    The waitlists schema.

    This is meant to serve as the common and generic schemas to
    all waitlists.
    """

    name: str = Field(
        min_length=1,
        description="Basket slug for the waitlist",
        examples=["new-product"],
    )
    source: AnyUrlString | None = Field(
        default=None,
        description="Source URL of subscription",
        examples=["https://www.mozilla.org/en-US/"],
    )
    fields: dict = Field(default={}, description="Additional fields", examples=['{"platform": "linux"}'])
    subscribed: bool = Field(default=True, description="True to subscribe, False to unsubscribe")
    unsub_reason: str | None = Field(default=None, description="Reason for unsubscribing")

    def __lt__(self, other):
        return self.name < other.name

    @model_validator(mode="after")
    def check_fields(self):
        """
        Once waitlists will have been migrated to a full N-N relationship,
        this will be the only remaining VPN specific piece of code.
        """
        if self.name == "relay":

            class RelayFieldsSchema(ComparableBase):
                geo: str | None = CountryField()
                model_config = ConfigDict(extra="forbid")

            RelayFieldsSchema(**self.fields)

        elif self.name == "vpn":

            class VPNFieldsSchema(ComparableBase):
                geo: str | None = CountryField()
                platform: str | None = PlatformField()
                model_config = ConfigDict(extra="forbid")

            VPNFieldsSchema(**self.fields)

        else:
            # Default schema for any waitlist.
            # Only the known fields are validated. Any extra field would
            # be accepted as is.
            # This should allow us to onboard most waitlists without specific
            # code change and service redeployment.
            class DefaultFieldsSchema(ComparableBase):
                geo: str | None = CountryField()
                platform: str | None = PlatformField()

            DefaultFieldsSchema(**self.fields)

        return self

    model_config = ConfigDict(from_attributes=True)


# No need to change anything, just extend if you want to
WaitlistSchema = WaitlistBase


WaitlistInSchema = WaitlistBase


class WaitlistTimestampedSchema(WaitlistBase):
    create_timestamp: ZeroOffsetDatetime = Field(
        description="Waitlist data creation timestamp",
        examples=["2020-12-05T19:21:50.908000+00:00"],
    )
    update_timestamp: ZeroOffsetDatetime = Field(
        description="Waitlist data update timestamp",
        examples=["2021-02-04T15:36:57.511000+00:00"],
    )


class WaitlistTableSchema(WaitlistTimestampedSchema):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        examples=[EMAIL_ID_EXAMPLE],
    )
    model_config = ConfigDict(extra="forbid")


def CountryField():
    return Field(
        default=None,
        max_length=100,
        description="Waitlist country",
        examples=["fr"],
    )


def PlatformField():
    return Field(
        default=None,
        max_length=100,
        description="VPN waitlist platforms as comma-separated list",
        examples=["ios,mac"],
    )


class RelayWaitlistSchema(ComparableBase):
    """
    The Mozilla Relay Waitlist schema for the read-only `relay_waitlist` field.
    """

    geo: str | None = Field(
        default=None,
        max_length=100,
        description="Relay waitlist country",
        examples=["fr"],
    )
    model_config = ConfigDict(from_attributes=True)


class VpnWaitlistSchema(ComparableBase):
    """
    The Mozilla VPN Waitlist schema for the read-only `vpn_waitlist` field
    """

    geo: str | None = Field(
        default=None,
        max_length=100,
        description="VPN waitlist country, FPN_Waitlist_Geo__c in Salesforce",
        examples=["fr"],
    )
    platform: str | None = Field(
        default=None,
        max_length=100,
        description="VPN waitlist platforms as comma-separated list, FPN_Waitlist_Platform__c in Salesforce",
        examples=["ios,mac"],
    )
    model_config = ConfigDict(from_attributes=True)
