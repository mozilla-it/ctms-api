from datetime import datetime
from typing import Optional

from pydantic import UUID4, AnyUrl, Field, root_validator

from .base import ComparableBase
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE


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
        example="new-product",
    )
    source: Optional[AnyUrl] = Field(
        default=None,
        description="Source URL of subscription",
        example="https://www.mozilla.org/en-US/",
    )
    fields: dict = Field(
        default={}, description="Additional fields", example='{"platform": "linux"}'
    )
    subscribed: bool = Field(
        default=True, description="True to subscribe, False to unsubscribe"
    )
    unsub_reason: Optional[str] = Field(
        default=None, description="Reason for unsubscribing"
    )

    def __lt__(self, other):
        return self.name < other.name

    @root_validator
    def check_fields(cls, values):  # pylint:disable = no-self-argument
        validate_waitlist_fields(values.get("name"), values.get("fields", {}))
        return values

    class Config:
        orm_mode = True


# No need to change anything, just extend if you want to
WaitlistSchema = WaitlistBase


WaitlistInSchema = WaitlistBase


class WaitlistTimestampedSchema(WaitlistBase):
    create_timestamp: datetime = Field(
        description="Waitlist data creation timestamp",
        example="2020-12-05T19:21:50.908000+00:00",
    )
    update_timestamp: datetime = Field(
        description="Waitlist data update timestamp",
        example="2021-02-04T15:36:57.511000+00:00",
    )


class WaitlistTableSchema(WaitlistTimestampedSchema):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        example=EMAIL_ID_EXAMPLE,
    )

    class Config:
        extra = "forbid"


def CountryField():  # pylint:disable = invalid-name
    return Field(
        default=None,
        max_length=100,
        description="Waitlist country",
        example="fr",
    )


def PlatformField():  # pylint:disable = invalid-name
    return Field(
        default=None,
        max_length=100,
        description="VPN waitlist platforms as comma-separated list",
        example="ios,mac",
    )


def validate_waitlist_fields(name: Optional[str], fields: dict):
    """
    Once waitlists will have been migrated to a full N-N relationship,
    this will be the only remaining VPN specific piece of code.
    """
    if name == "relay":

        class RelayFieldsSchema(ComparableBase):
            geo: Optional[str] = CountryField()

            class Config:
                extra = "forbid"

        RelayFieldsSchema(**fields)

    elif name == "vpn":

        class VPNFieldsSchema(ComparableBase):
            geo: Optional[str] = CountryField()
            platform: Optional[str] = PlatformField()

            class Config:
                extra = "forbid"

        VPNFieldsSchema(**fields)

    else:
        # Default schema for any waitlist.
        # Only the known fields are validated. Any extra field would
        # be accepted as is.
        # This should allow us to onboard most waitlists without specific
        # code change and service redeployment.
        class DefaultFieldsSchema(ComparableBase):
            geo: Optional[str] = CountryField()
            platform: Optional[str] = PlatformField()

        DefaultFieldsSchema(**fields)


def validate_waitlist_newsletters(values):
    """
    This helper validates that when subscribing to `relay-*-waitlist`
    newsletters, the country is provided.
    # TODO waitlist: remove once Basket leverages the `waitlists` field.
    """
    if "newsletters" not in values:
        return values

    newsletters = values["newsletters"]
    if not isinstance(newsletters, list):
        return values

    relay_newsletter_found = False
    for newsletter in newsletters:
        if newsletter.subscribed and newsletter.name.startswith("relay-"):
            relay_newsletter_found = True
            break

    if not relay_newsletter_found:
        return values

    # If specified using the legacy `relay_waitlist`
    relay_country = None
    relay_waitlist = values.get("relay_waitlist")
    if relay_waitlist:
        relay_country = relay_waitlist.geo
    elif "waitlists" in values:
        # If specified using the `waitlists` field (unlikely, but in our tests we do)
        waitlists = values["waitlists"]
        if isinstance(waitlists, list):
            for waitlist in waitlists:
                if waitlist.name == "relay":
                    relay_country = waitlist.fields.get("geo")

    # Relay country not specified, check if a relay newsletter is being subscribed.
    if not relay_country:
        raise ValueError("Relay country missing")

    return values


class RelayWaitlistBase(ComparableBase):
    """
    The Mozilla Relay Waitlist schema.

    TODO waitlist: remove once Basket leverages the `waitlists` field.
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
