from typing import List, Literal, Optional, Set
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from .addons import AddOnsInSchema, AddOnsSchema
from .base import ComparableBase
from .email import EmailBase, EmailInSchema, EmailPutSchema, EmailSchema
from .fxa import FirefoxAccountsInSchema, FirefoxAccountsSchema
from .newsletter import NewsletterInSchema, NewsletterSchema
from .vpn import VpnWaitlistInSchema, VpnWaitlistSchema


class ContactSchema(ComparableBase):
    """A complete contact."""

    amo: Optional[AddOnsSchema] = None
    email: EmailSchema
    fxa: Optional[FirefoxAccountsSchema] = None
    newsletters: List[NewsletterSchema] = Field(
        default=[],
        description="List of newsletters for which the contact is or was subscribed",
        example=([{"name": "firefox-welcome"}, {"name": "mozilla-welcome"}]),
    )
    vpn_waitlist: Optional[VpnWaitlistSchema] = None

    def as_identity_response(self) -> "IdentityResponse":
        """Return the identities of a contact"""
        return IdentityResponse(
            amo_user_id=getattr(self.amo, "user_id", None),
            basket_token=getattr(self.email, "basket_token", None),
            email_id=getattr(self.email, "email_id", None),
            fxa_id=getattr(self.fxa, "fxa_id", None),
            fxa_primary_email=getattr(self.fxa, "primary_email", None),
            mofo_id=getattr(self.email, "mofo_id", None),
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
        if (
            hasattr(self, "vpn_waitlist")
            and self.vpn_waitlist
            and self.vpn_waitlist.is_default()
        ):
            default_fields.add("vpn_waitlist")
        if all(n.is_default() for n in self.newsletters):
            default_fields.add("newsletters")
        return default_fields


class ContactInBase(ComparableBase):
    """A contact as provided by callers."""

    amo: Optional[AddOnsInSchema] = None
    email: EmailBase
    fxa: Optional[FirefoxAccountsInSchema] = None
    newsletters: List[NewsletterInSchema] = Field(
        default=[],
        description="List of newsletters for which the contact is or was subscribed",
        example=([{"name": "firefox-welcome"}, {"name": "mozilla-welcome"}]),
    )
    vpn_waitlist: Optional[VpnWaitlistInSchema] = None

    def idempotent_equal(self, other):
        def _noneify(field):
            if not field:
                return None
            return None if field.is_default() else field

        if self.email != other.email:
            return False
        if _noneify(self.amo) != _noneify(other.amo):
            return False
        if _noneify(self.fxa) != _noneify(other.fxa):
            return False
        if _noneify(self.vpn_waitlist) != _noneify(other.vpn_waitlist):
            return False
        if sorted(self.newsletters) != sorted(other.newsletters):
            return False
        return True


class ContactInSchema(ContactInBase):
    """A contact as provided by callers when using POST. This is nearly identical to the ContactPutSchema but doesn't require an email_id."""

    email: EmailInSchema


class ContactPutSchema(ContactInBase):
    """A contact as provided by callers when using POST. This is nearly identical to the ContactInSchema but does require an email_id."""

    email: EmailPutSchema


class CTMSResponse(BaseModel):
    """
    Response for /ctms/<email_id>

    Similar to ContactSchema, but groups are required and includes status: OK
    """

    amo: AddOnsSchema
    email: EmailSchema
    fxa: FirefoxAccountsSchema
    newsletters: List[NewsletterSchema]
    status: Literal["ok"] = Field(
        default="ok", description="Request was successful", example="ok"
    )
    vpn_waitlist: VpnWaitlistSchema


class IdentityResponse(BaseModel):
    """The identity keys for a contact."""

    email_id: UUID
    primary_email: EmailStr
    basket_token: UUID
    sfdc_id: Optional[str] = None
    mofo_id: Optional[str] = None
    amo_user_id: Optional[str] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[EmailStr] = None
