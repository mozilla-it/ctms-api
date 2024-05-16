from datetime import datetime
from typing import TYPE_CHECKING, List, Literal, Optional, Union
from uuid import UUID

from pydantic import AnyUrl, BaseModel, Field, root_validator, validator

from .addons import AddOnsInSchema, AddOnsSchema
from .base import ComparableBase
from .email import (
    EmailBase,
    EmailInSchema,
    EmailPatchSchema,
    EmailPutSchema,
    EmailSchema,
)
from .fxa import FirefoxAccountsInSchema, FirefoxAccountsSchema
from .mofo import MozillaFoundationInSchema, MozillaFoundationSchema
from .newsletter import (
    NewsletterInSchema,
    NewsletterSchema,
    NewsletterTableSchema,
    NewsletterTimestampedSchema,
)
from .waitlist import (
    RelayWaitlistInSchema,
    RelayWaitlistSchema,
    VpnWaitlistInSchema,
    VpnWaitlistSchema,
    WaitlistInSchema,
    WaitlistSchema,
    WaitlistTableSchema,
    WaitlistTimestampedSchema,
    validate_waitlist_newsletters,
)

if TYPE_CHECKING:
    from ctms.models import Email


class ContactSchema(ComparableBase):
    """A complete contact."""

    amo: Optional[AddOnsSchema] = None
    email: EmailSchema
    fxa: Optional[FirefoxAccountsSchema] = None
    mofo: Optional[MozillaFoundationSchema] = None
    newsletters: List[NewsletterTableSchema] = []
    waitlists: List[WaitlistTableSchema] = []

    @classmethod
    def from_email(cls, email: "Email") -> "ContactSchema":
        return cls(
            amo=email.amo,
            email=email,
            fxa=email.fxa,
            mofo=email.mofo,
            newsletters=email.newsletters,
            waitlists=email.waitlists,
        )

    class Config:
        fields = {
            "newsletters": {
                "description": "List of newsletters for which the contact is or was subscribed",
                "example": [
                    {
                        "name": "firefox-welcome",
                        "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                        "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                        "email_id": EmailSchema.schema()["properties"]["email_id"][
                            "example"
                        ],
                    },
                    {
                        "name": "mozilla-welcome",
                        "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                        "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                        "email_id": EmailSchema.schema()["properties"]["email_id"][
                            "example"
                        ],
                    },
                ],
            },
            "waitlists": {
                "description": "List of waitlists for which the contact is or was subscribed",
                "example": [
                    {
                        "name": "example-product",
                        "fields": {"geo": "fr", "platform": "win64"},
                        "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                        "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                        "email_id": EmailSchema.schema()["properties"]["email_id"][
                            "example"
                        ],
                    },
                    {
                        "name": "relay",
                        "fields": {"geo": "fr"},
                        "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                        "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                        "email_id": EmailSchema.schema()["properties"]["email_id"][
                            "example"
                        ],
                    },
                    {
                        "name": "vpn",
                        "fields": {"geo": "fr", "platform": "ios,mac"},
                        "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                        "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                        "email_id": EmailSchema.schema()["properties"]["email_id"][
                            "example"
                        ],
                    },
                ],
            },
        }

    def as_identity_response(self) -> "IdentityResponse":
        """Return the identities of a contact"""
        return IdentityResponse(
            amo_user_id=getattr(self.amo, "user_id", None),
            basket_token=getattr(self.email, "basket_token", None),
            email_id=getattr(self.email, "email_id", None),
            fxa_id=getattr(self.fxa, "fxa_id", None),
            fxa_primary_email=getattr(self.fxa, "primary_email", None),
            mofo_contact_id=getattr(self.mofo, "mofo_contact_id", None),
            mofo_email_id=getattr(self.mofo, "mofo_email_id", None),
            primary_email=getattr(self.email, "primary_email", None),
            sfdc_id=getattr(self.email, "sfdc_id", None),
        )


class ContactInBase(ComparableBase):
    """A contact as provided by callers."""

    amo: Optional[AddOnsInSchema] = None
    email: EmailBase
    fxa: Optional[FirefoxAccountsInSchema] = None
    mofo: Optional[MozillaFoundationInSchema] = None
    newsletters: List[NewsletterInSchema] = []
    waitlists: List[WaitlistInSchema] = []
    # TODO waitlist: remove once Basket leverages the `waitlists` field.
    vpn_waitlist: Optional[VpnWaitlistInSchema] = None
    relay_waitlist: Optional[RelayWaitlistInSchema] = None

    class Config:
        fields = ContactSchema.Config.fields

    @root_validator
    def check_fields(cls, values):  # pylint:disable = no-self-argument
        """
        This makes sure a Relay country is specified when one of the `relay-*-waitlist`
        newsletter is subscribed.

        TODO waitlist: remove once Basket leverages the `waitlists` field.
        """
        return validate_waitlist_newsletters(values)

    def idempotent_equal(self, other):
        def _noneify(field):
            if not field:
                return None
            return None if field.is_default() else field

        return (
            self.email == other.email
            and _noneify(self.amo) == _noneify(other.amo)
            and _noneify(self.fxa) == _noneify(other.fxa)
            and _noneify(self.mofo) == _noneify(other.mofo)
            and sorted(self.newsletters) == sorted(other.newsletters)
            and sorted(self.waitlists) == sorted(other.waitlists)
        )


class ContactInSchema(ContactInBase):
    """A contact as provided by callers when using POST. This is nearly identical to the ContactPutSchema but doesn't require an email_id."""

    email: EmailInSchema


class ContactPutSchema(ContactInBase):
    """A contact as provided by callers when using PUT. This is nearly identical to the ContactInSchema but does require an email_id."""

    email: EmailPutSchema


class ContactPatchSchema(ComparableBase):
    """A contact provided by callers when using PATCH.

    This is nearly identical to ContactInSchema, but almost everything
    is optional, and some values can be action strings (like "DELETE" or
    "UNSUBSCRIBE" instead of lists or objects.
    """

    amo: Optional[Union[Literal["DELETE"], AddOnsInSchema]]
    email: Optional[EmailPatchSchema]
    fxa: Optional[Union[Literal["DELETE"], FirefoxAccountsInSchema]]
    mofo: Optional[Union[Literal["DELETE"], MozillaFoundationInSchema]]
    newsletters: Optional[Union[List[NewsletterSchema], Literal["UNSUBSCRIBE"]]]
    waitlists: Optional[Union[List[WaitlistInSchema], Literal["UNSUBSCRIBE"]]]
    # TODO waitlist: remove once Basket leverages the `waitlists` field.
    vpn_waitlist: Optional[Union[Literal["DELETE"], VpnWaitlistInSchema]]
    relay_waitlist: Optional[Union[Literal["DELETE"], RelayWaitlistInSchema]]

    @root_validator
    def check_fields(cls, values):  # pylint:disable = no-self-argument
        """
        This makes sure a Relay country is specified when one of the `relay-*-waitlist`
        newsletter is subscribed.

        TODO waitlist: remove once Basket leverages the `waitlists` field.
        """
        return validate_waitlist_newsletters(values)

    class Config:
        fields = {
            "amo": {"description": 'Add-ons data to update, or "DELETE" to reset.'},
            "fxa": {
                "description": 'Firefox Accounts data to update, or "DELETE" to reset.'
            },
            "mofo": {
                "description": 'Mozilla Foundation data to update, or "DELETE" to reset.'
            },
            "newsletters": {
                "description": (
                    "List of newsletters to add or update, or 'UNSUBSCRIBE' to"
                    " unsubscribe from all."
                ),
                "example": [{"name": "firefox-welcome", "subscribed": False}],
            },
            "vpn_waitlist": {
                "description": 'VPN Waitlist data to update, or "DELETE" to reset.'
            },
            "relay_waitlist": {
                "description": 'Relay Waitlist data to update, or "DELETE" to reset.'
            },
            "waitlists": {
                "description": ("List of waitlists to add or update."),
                "example": [
                    {
                        "name": "example-product",
                        "fields": {"geo": "fr", "platform": "win64"},
                    }
                ],
            },
        }


class CTMSResponse(BaseModel):
    """
    Response for GET /ctms/ by alternate IDs

    Similar to ContactSchema, but groups are required
    """

    amo: AddOnsSchema
    email: EmailSchema
    fxa: FirefoxAccountsSchema
    mofo: MozillaFoundationSchema
    newsletters: List[NewsletterTimestampedSchema]
    waitlists: List[WaitlistTimestampedSchema]
    # Retro-compat fields
    vpn_waitlist: VpnWaitlistSchema
    relay_waitlist: RelayWaitlistSchema

    @validator("amo", pre=True, always=True)
    def set_default_amo(cls, value):  # pylint: disable=no-self-argument
        return value or AddOnsSchema()

    @validator("fxa", pre=True, always=True)
    def set_default_fxa(cls, value):  # pylint: disable=no-self-argument
        return value or FirefoxAccountsSchema()

    @validator("mofo", pre=True, always=True)
    def set_default_mofo(cls, value):  # pylint: disable=no-self-argument
        return value or MozillaFoundationSchema()

    @root_validator(pre=True)
    def legacy_waitlists(cls, values):  # pylint: disable=no-self-argument
        # Show computed fields in response for retro-compatibility.
        values["vpn_waitlist"] = VpnWaitlistSchema()
        values["relay_waitlist"] = RelayWaitlistSchema()
        for waitlist in values.get("waitlists", []):
            if not waitlist["subscribed"]:
                # Ignore unsubscribed waitlists...
                continue
            if isinstance(waitlist, dict):
                # TODO: figure out why dict from `response_model` decorators param in app.py)
                waitlist = WaitlistSchema(**waitlist)
            if waitlist.name == "vpn":
                values["vpn_waitlist"] = VpnWaitlistSchema(
                    geo=waitlist.fields.get("geo"),
                    platform=waitlist.fields.get("platform"),
                )
            # If multiple `relay-` waitlists are present, the `geo` field of the
            # first waitlist is set as the value of `relay_waitlist["geo"]`. This
            # property is intended for legacy consumers. New consumers should prefer the
            # `waitlists` property of the contact schema
            if (
                waitlist.name.startswith("relay")
                and values["relay_waitlist"].geo is None
            ):
                values["relay_waitlist"] = RelayWaitlistSchema(
                    geo=waitlist.fields.get("geo")
                )

        return values


class CTMSSingleResponse(CTMSResponse):
    """
    Response for /ctms/<email_id>

    Similar to ContactSchema, but groups are required and includes status: OK
    """

    status: Literal["ok"] = Field(
        default="ok", description="Request was successful", example="ok"
    )


class CTMSBulkResponse(BaseModel):
    """
    Response for GET /updates/

    """

    start: datetime
    end: datetime
    limit: int
    after: Optional[str] = None
    next: Optional[Union[AnyUrl, str]] = None
    items: List[CTMSResponse]


class IdentityResponse(BaseModel):
    """The identity keys for a contact."""

    email_id: UUID
    primary_email: str
    basket_token: Optional[UUID] = None
    sfdc_id: Optional[str] = None
    mofo_contact_id: Optional[str] = None
    mofo_email_id: Optional[str] = None
    amo_user_id: Optional[str] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[str] = None
