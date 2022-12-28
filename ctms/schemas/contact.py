from datetime import datetime
from typing import List, Literal, Optional, Set, Union
from uuid import UUID

from pydantic import AnyUrl, BaseModel, Field

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
from .newsletter import NewsletterInSchema, NewsletterSchema
from .product import ProductBaseSchema
from .waitlist import (
    RelayWaitlistInSchema,
    RelayWaitlistSchema,
    VpnWaitlistInSchema,
    VpnWaitlistSchema,
    WaitlistInSchema,
    WaitlistSchema,
)


class ContactSchema(ComparableBase):
    """A complete contact."""

    amo: Optional[AddOnsSchema] = None
    email: EmailSchema
    fxa: Optional[FirefoxAccountsSchema] = None
    mofo: Optional[MozillaFoundationSchema] = None
    newsletters: List[NewsletterSchema] = []
    waitlists: List[WaitlistSchema] = []
    products: List[ProductBaseSchema] = []

    class Config:
        fields = {
            "newsletters": {
                "description": "List of newsletters for which the contact is or was subscribed",
                "example": [{"name": "firefox-welcome"}, {"name": "mozilla-welcome"}],
            },
            "waitlists": {
                "description": "List of waitlists for which the contact is or was subscribed",
                "example": [
                    {
                        "name": "example-product",
                        "geo": "fr",
                        "fields": {"platform": "win64"},
                    },
                    {
                        "name": "relay",
                        "geo": "fr",
                    },
                    {
                        "name": "vpn",
                        "geo": "fr",
                        "fields": {"platform": "ios,mac"},
                    },
                ],
            },
        }

    @property
    def relay_waitlist(self):
        """Mimic legacy fields by looking for the first Relay entry in the Waitlist table."""
        # Iterate `waitlists` since it is likely to be already populated by a join in `crud.py`
        for waitlist in self.waitlists:
            if waitlist.name.startswith("relay"):
                return RelayWaitlistSchema(geo=waitlist.geo)
        return None

    @property
    def vpn_waitlist(self):
        """Mimic legacy fields by looking for a VPN entry in the Waitlist table."""
        # Iterate `waitlists` since it is likely to be already populated by a join in `crud.py`
        for waitlist in self.waitlists:
            if waitlist.name == "vpn":
                return VpnWaitlistSchema(
                    geo=waitlist.geo,
                    platform=waitlist.fields.get("platform"),
                )
        return None

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

    def find_default_fields(self) -> Set[str]:
        """Return names of fields that contain default values only"""
        default_fields = set()
        if hasattr(self, "amo") and self.amo and self.amo.is_default():
            default_fields.add("amo")
        if hasattr(self, "fxa") and self.fxa and self.fxa.is_default():
            default_fields.add("fxa")
        if hasattr(self, "mofo") and self.mofo and self.mofo.is_default():
            default_fields.add("mofo")
        if all(n.is_default() for n in self.newsletters):
            default_fields.add("newsletters")
        if all(n.is_default() for n in self.waitlists):
            default_fields.add("waitlists")
        return default_fields


class ContactInBase(ComparableBase):
    """A contact as provided by callers."""

    amo: Optional[AddOnsInSchema] = None
    email: EmailBase
    fxa: Optional[FirefoxAccountsInSchema] = None
    mofo: Optional[MozillaFoundationInSchema] = None
    newsletters: List[NewsletterInSchema] = []
    waitlists: List[WaitlistInSchema] = []
    # Retro-compat fields. Drop once Basket uses the `waitlists` list.
    vpn_waitlist: Optional[VpnWaitlistInSchema] = None
    relay_waitlist: Optional[RelayWaitlistInSchema] = None

    class Config:
        fields = ContactSchema.Config.fields

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
    # Retro-compat fields. Drop once Basket uses the `waitlists` list.
    vpn_waitlist: Optional[Union[Literal["DELETE"], VpnWaitlistInSchema]]
    relay_waitlist: Optional[Union[Literal["DELETE"], RelayWaitlistInSchema]]

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
                        "geo": "fr",
                        "fields": {"platform": "win64"},
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
    newsletters: List[NewsletterSchema]
    waitlists: List[WaitlistSchema]
    # Retro-compat fields
    vpn_waitlist: VpnWaitlistSchema
    relay_waitlist: RelayWaitlistSchema

    def __init__(self, *args, **kwargs) -> None:
        # Show computed fields in response for retro-compatibility.
        kwargs["vpn_waitlist"] = VpnWaitlistSchema()
        kwargs["relay_waitlist"] = RelayWaitlistSchema()

        for waitlist in kwargs.get("waitlists", []):
            if isinstance(waitlist, dict):
                # TODO: figure out why dict from `response_model` decorators param in app.py)
                waitlist = WaitlistSchema(**waitlist)
            if isinstance(waitlist, WaitlistInSchema):
                # Many tests instantiates CTMSResponse with `WaitlistInSchema` (input schema).
                waitlist = WaitlistSchema(**waitlist.dict())
            if waitlist.name == "vpn":
                kwargs["vpn_waitlist"] = VpnWaitlistSchema(
                    geo=waitlist.geo,
                    platform=waitlist.fields.get("platform"),
                )
            if waitlist.name.startswith("relay"):
                kwargs["relay_waitlist"] = RelayWaitlistSchema(geo=waitlist.geo)
        super().__init__(*args, **kwargs)


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
    basket_token: UUID
    sfdc_id: Optional[str] = None
    mofo_contact_id: Optional[str] = None
    mofo_email_id: Optional[str] = None
    amo_user_id: Optional[str] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[str] = None
