from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from pydantic import UUID4, AnyUrl, ConfigDict, Field, model_validator

from .base import ComparableBase
from .common import ZeroOffsetDatetime
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE

if TYPE_CHECKING:
    from .contact import ContactInBase, ContactPatchSchema


class WaitlistBase(ComparableBase):
    """
    The waitlists schema.

    This is meant to serve as the common and generic schemas to
    all waitlists.

    In this implementation phase, it cohabits with individual (non-generic)
    schemas of Relay and VPN.

    TODO waitlist: once Basket leverages the `waitlists` field, we can drop
    `RelayWaitlistBase` and `VpnWaitlistBase`.
    """

    name: str = Field(
        min_length=1,
        description="Basket slug for the waitlist",
        examples=["new-product"],
    )
    source: Optional[AnyUrl] = Field(
        default=None,
        description="Source URL of subscription",
        examples=["https://www.mozilla.org/en-US/"],
    )
    fields: dict = Field(
        default={}, description="Additional fields", examples=['{"platform": "linux"}']
    )
    subscribed: bool = Field(
        default=True, description="True to subscribe, False to unsubscribe"
    )
    unsub_reason: Optional[str] = Field(
        default=None, description="Reason for unsubscribing"
    )

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
                geo: Optional[str] = CountryField()
                model_config = ConfigDict(extra="forbid")

            RelayFieldsSchema(**self.fields)

        elif self.name == "vpn":

            class VPNFieldsSchema(ComparableBase):
                geo: Optional[str] = CountryField()
                platform: Optional[str] = PlatformField()
                model_config = ConfigDict(extra="forbid")

            VPNFieldsSchema(**self.fields)

        else:
            # Default schema for any waitlist.
            # Only the known fields are validated. Any extra field would
            # be accepted as is.
            # This should allow us to onboard most waitlists without specific
            # code change and service redeployment.
            class DefaultFieldsSchema(ComparableBase):
                geo: Optional[str] = CountryField()
                platform: Optional[str] = PlatformField()

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


def CountryField():  # pylint:disable = invalid-name
    return Field(
        default=None,
        max_length=100,
        description="Waitlist country",
        examples=["fr"],
    )


def PlatformField():  # pylint:disable = invalid-name
    return Field(
        default=None,
        max_length=100,
        description="VPN waitlist platforms as comma-separated list",
        examples=["ios,mac"],
    )


def validate_waitlist_newsletters(
    contact: Union["ContactInBase", "ContactPatchSchema"]
):
    """
    This helper validates that when subscribing to `relay-*-waitlist`
    newsletters, the country is provided.
    # TODO waitlist: remove once Basket leverages the `waitlists` field.
    """
    if not contact.newsletters:
        return contact

    if not isinstance(contact.newsletters, list):
        return contact

    relay_newsletter_found = False
    for newsletter in contact.newsletters:
        if newsletter.subscribed and newsletter.name.startswith("relay-"):
            relay_newsletter_found = True
            break

    if not relay_newsletter_found:
        return contact

    # If specified using the legacy `relay_waitlist`
    relay_country = None
    relay_waitlist = contact.relay_waitlist
    if relay_waitlist and relay_waitlist != "DELETE":
        relay_country = relay_waitlist.geo
    elif hasattr(contact, "waitlists"):
        # If specified using the `waitlists` field (unlikely, but in our tests we do)
        if isinstance(contact.waitlists, list):
            for waitlist in contact.waitlists:
                if waitlist.name == "relay":
                    relay_country = waitlist.fields.get("geo")

    # Relay country not specified, check if a relay newsletter is being subscribed.
    if not relay_country:
        raise ValueError("Relay country missing")

    return contact


class RelayWaitlistBase(ComparableBase):
    """
    The Mozilla Relay Waitlist schema.

    TODO waitlist: remove once Basket leverages the `waitlists` field.
    """

    geo: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Relay waitlist country",
        examples=["fr"],
    )
    model_config = ConfigDict(from_attributes=True)


# No need to change anything, just extend if you want to
RelayWaitlistInSchema = RelayWaitlistBase
RelayWaitlistSchema = RelayWaitlistBase


class VpnWaitlistBase(ComparableBase):
    """
    The Mozilla VPN Waitlist schema.

    This was previously the Firefox Private Network (fpn) waitlist data,
    with a similar purpose.

    TODO waitlist: remove once Basket leverages the `waitlists` field.
    """

    geo: Optional[str] = Field(
        default=None,
        max_length=100,
        description="VPN waitlist country, FPN_Waitlist_Geo__c in Salesforce",
        examples=["fr"],
    )
    platform: Optional[str] = Field(
        default=None,
        max_length=100,
        description=(
            "VPN waitlist platforms as comma-separated list,"
            " FPN_Waitlist_Platform__c in Salesforce"
        ),
        examples=["ios,mac"],
    )
    model_config = ConfigDict(from_attributes=True)


# No need to change anything, just extend if you want to
VpnWaitlistInSchema = VpnWaitlistBase
VpnWaitlistSchema = VpnWaitlistBase
