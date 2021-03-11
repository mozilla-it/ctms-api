from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import UUID4, BaseModel, EmailStr, Field, HttpUrl

from .addons import AddOnsInSchema, AddOnsSchema
from .base import ComparableBase
from .email import EmailInSchema, EmailSchema
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


class ContactInSchema(ComparableBase):
    """A contact as provided by callers."""

    amo: Optional[AddOnsInSchema] = None
    email: EmailInSchema
    fxa: Optional[FirefoxAccountsInSchema] = None
    newsletters: List[NewsletterInSchema] = Field(
        default=[],
        description="List of newsletters for which the contact is or was subscribed",
        example=([{"name": "firefox-welcome"}, {"name": "mozilla-welcome"}]),
    )
    vpn_waitlist: Optional[VpnWaitlistInSchema] = None

    def idempotent_equal(self, other):
        # settings = {"exclude_defaults": True, "exclude_unset": True}
        # print(self.dict(**settings), other.dict(**settings))
        # return self.dict(**settings) == other.dict(**settings)
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
