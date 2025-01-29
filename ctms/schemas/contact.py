from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from .addons import AddOnsInSchema, AddOnsSchema
from .base import ComparableBase
from .common import AnyUrlString
from .email import (
    EMAIL_ID_EXAMPLE,
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
    RelayWaitlistSchema,
    VpnWaitlistSchema,
    WaitlistInSchema,
    WaitlistSchema,
    WaitlistTableSchema,
    WaitlistTimestampedSchema,
)

if TYPE_CHECKING:
    from ctms.models import Email


class ContactSchema(ComparableBase):
    """A complete contact."""

    amo: AddOnsSchema | None = None
    email: EmailSchema
    fxa: FirefoxAccountsSchema | None = None
    mofo: MozillaFoundationSchema | None = None
    newsletters: list[NewsletterTableSchema] = Field(
        default_factory=list,
        description="List of newsletters for which the contact is or was subscribed",
        examples=[
            [
                {
                    "name": "firefox-welcome",
                    "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                    "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                    "email_id": EMAIL_ID_EXAMPLE,
                },
                {
                    "name": "mozilla-welcome",
                    "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                    "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                    "email_id": EMAIL_ID_EXAMPLE,
                },
            ]
        ],
    )
    waitlists: list[WaitlistTableSchema] = Field(
        default_factory=list,
        description="List of waitlists for which the contact is or was subscribed",
        examples=[
            [
                {
                    "name": "example-product",
                    "fields": {"geo": "fr", "platform": "win64"},
                    "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                    "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                    "email_id": EMAIL_ID_EXAMPLE,
                },
                {
                    "name": "relay",
                    "fields": {"geo": "fr"},
                    "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                    "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                    "email_id": EMAIL_ID_EXAMPLE,
                },
                {
                    "name": "vpn",
                    "fields": {"geo": "fr", "platform": "ios,mac"},
                    "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                    "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
                    "email_id": EMAIL_ID_EXAMPLE,
                },
            ]
        ],
    )

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

    amo: AddOnsInSchema | None = None
    email: EmailBase
    fxa: FirefoxAccountsInSchema | None = None
    mofo: MozillaFoundationInSchema | None = None
    newsletters: list[NewsletterInSchema] = Field(
        default_factory=list,
        examples=[
            [
                {
                    "name": "firefox-welcome",
                },
                {
                    "name": "mozilla-welcome",
                },
            ]
        ],
    )
    waitlists: list[WaitlistInSchema] = Field(
        default_factory=list,
        examples=[
            [
                {
                    "name": "example-product",
                    "fields": {"geo": "fr", "platform": "win64"},
                },
                {
                    "name": "relay",
                    "fields": {"geo": "fr"},
                },
            ]
        ],
    )

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

    amo: Literal["DELETE"] | AddOnsInSchema | None = Field(None, description='Add-ons data to update, or "DELETE" to reset.')
    email: EmailPatchSchema | None = None
    fxa: Literal["DELETE"] | FirefoxAccountsInSchema | None = Field(None, description='Firefox Accounts data to update, or "DELETE" to reset.')
    mofo: Literal["DELETE"] | MozillaFoundationInSchema | None = Field(None, description='Mozilla Foundation data to update, or "DELETE" to reset.')
    newsletters: list[NewsletterSchema] | Literal["UNSUBSCRIBE"] | None = Field(
        None,
        description="List of newsletters to add or update, or 'UNSUBSCRIBE' to unsubscribe from all.",
        examples=[[{"name": "firefox-welcome", "subscribed": False}]],
    )
    waitlists: list[WaitlistInSchema] | Literal["UNSUBSCRIBE"] | None = Field(
        None,
        description="List of waitlists to add or update.",
        examples=[
            [
                {
                    "name": "example-product",
                    "fields": {"geo": "fr", "platform": "win64"},
                }
            ]
        ],
    )


class CTMSResponse(BaseModel):
    """
    Response for GET /ctms/ by alternate IDs

    Similar to ContactSchema, but groups are required
    """

    amo: AddOnsSchema
    email: EmailSchema
    fxa: FirefoxAccountsSchema
    mofo: MozillaFoundationSchema
    newsletters: list[NewsletterTimestampedSchema]
    waitlists: list[WaitlistTimestampedSchema]
    # Retro-compat fields
    vpn_waitlist: VpnWaitlistSchema
    relay_waitlist: RelayWaitlistSchema

    @field_validator("amo", mode="before")
    @classmethod
    def set_default_amo(cls, value):
        return value or AddOnsSchema()

    @field_validator("fxa", mode="before")
    @classmethod
    def set_default_fxa(cls, value):
        return value or FirefoxAccountsSchema()

    @field_validator("mofo", mode="before")
    @classmethod
    def set_default_mofo(cls, value):
        return value or MozillaFoundationSchema()

    @model_validator(mode="before")
    @classmethod
    def legacy_waitlists(cls, values):
        # Show computed fields in response for retro-compatibility.
        values["vpn_waitlist"] = VpnWaitlistSchema()
        values["relay_waitlist"] = RelayWaitlistSchema()
        for waitlist in values.get("waitlists", []):
            if not waitlist["subscribed"]:
                # Ignore unsubscribed waitlists...
                continue
            if isinstance(waitlist, dict):
                # TODO: figure out why dict from `response_model` decorators param in app.py)
                waitlist = WaitlistSchema(**waitlist)  # noqa: PLW2901
            if waitlist.name == "vpn":
                values["vpn_waitlist"] = VpnWaitlistSchema(
                    geo=waitlist.fields.get("geo"),
                    platform=waitlist.fields.get("platform"),
                )
            # If multiple `relay-` waitlists are present, the `geo` field of the
            # first waitlist is set as the value of `relay_waitlist["geo"]`. This
            # property is intended for legacy consumers. New consumers should prefer the
            # `waitlists` property of the contact schema
            if waitlist.name.startswith("relay") and values["relay_waitlist"].geo is None:
                values["relay_waitlist"] = RelayWaitlistSchema(geo=waitlist.fields.get("geo"))

        return values


class CTMSSingleResponse(CTMSResponse):
    """
    Response for /ctms/<email_id>

    Similar to ContactSchema, but groups are required and includes status: OK
    """

    status: Literal["ok"] = Field(default="ok", description="Request was successful", examples=["ok"])


class CTMSBulkResponse(BaseModel):
    """
    Response for GET /updates/

    """

    start: datetime
    end: datetime
    limit: int
    after: str | None = None
    next: AnyUrlString | str | None = None
    items: list[CTMSResponse]


class IdentityResponse(BaseModel):
    """The identity keys for a contact."""

    email_id: UUID
    primary_email: str
    basket_token: UUID | None = None
    sfdc_id: str | None = None
    mofo_contact_id: str | None = None
    mofo_email_id: str | None = None
    amo_user_id: str | None = None
    fxa_id: str | None = None
    fxa_primary_email: str | None = None
