from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class ContactSchema(BaseModel):
    """A complete contact."""

    id: UUID
    amo: Optional["ContactAmoSchema"] = None
    contact: Optional["ContactMainSchema"] = None
    cv: Optional["ContactCVSchema"] = None
    fpn: Optional["ContactFpnSchema"] = None
    fsa: Optional["ContactFsaSchema"] = None
    fxa: Optional["ContactFxaSchema"] = None
    newsletters: List[str] = []

    def as_identity_response(self) -> "IdentityResponse":
        """Return the identities of a contact"""
        return IdentityResponse(
            id=getattr(self.contact, "id", None),
            amo_id=getattr(self.amo, "id", None),
            fxa_id=getattr(self.fxa, "id", None),
            fxa_primary_email=getattr(self.fxa, "primary_email", None),
            token=getattr(self.contact, "token", None),
        )


class ContactAmoSchema(BaseModel):
    """
    The addons.mozilla.org data for a contact.

    TODO: user: When is this set true?
    - upsert_amo_user_data - set to True when User Sync request
      https://github.com/mozmeao/basket/blob/31941961e56c462a7d260f079c937e05ac0d9ae3/basket/news/tasks.py#L1137
    - amo_check_user_for_deletion - set to False when deleting a user
      https://github.com/mozmeao/basket/blob/31941961e56c462a7d260f079c937e05ac0d9ae3/basket/news/tasks.py#L1189
    """

    display_name: Optional[str] = None
    homepage: Optional[str] = None
    id: Optional[str] = None
    last_login: Optional[datetime] = None
    location: Optional[str] = None
    user: bool = False


class ContactMainSchema(BaseModel):
    """The "main" contact schema."""

    country: Optional[str] = None
    created_date: Optional[datetime] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    format: Literal["H", "T"] = "H"
    id: Optional[str] = None
    lang: Optional[str] = None
    last_modified_date: Optional[datetime] = None
    last_name: str = "_"
    optin: Optional[bool] = None
    optout: Optional[bool] = None
    payee_id: Optional[str] = None
    postal_code: Optional[str] = None
    reason: Optional[str] = None
    record_type: Optional[str] = None
    source_url: Optional[str] = None
    token: Optional[str] = None


class ContactCVSchema(BaseModel):
    """The CommonVoice schema."""

    created_at: Optional[datetime] = None
    days_interval: Optional[str] = None
    first_contribution_date: Optional[datetime] = None
    goal_reached_at: Optional[str] = None
    last_active_date: Optional[str] = None
    two_day_streak: Optional[str] = None


class ContactFpnSchema(BaseModel):
    """The Firefox Private Network schema."""

    country: Optional[str] = None
    platform: Optional[str] = None


class ContactFsaSchema(BaseModel):
    """
    The Firefox Student Ambassador program schema

    This is now at https://community.mozilla.org/en/, may not be used.
    """

    allow_share: Optional[str] = None
    city: Optional[str] = None
    current_status: Optional[str] = None
    grad_year: Optional[int] = None
    major: Optional[str] = None
    school: Optional[str] = None


class ContactFxaSchema(BaseModel):
    """The Firefox Account schema."""

    create_date: Optional[datetime] = None
    deleted: Optional[bool] = None
    id: Optional[str] = None
    lang: Optional[str] = None
    primary_email: Optional[str] = None
    service: Optional[str] = None


ContactSchema.update_forward_refs()


class CTMSResponse(BaseModel):
    """ContactSchema but sub-schemas are required."""

    id: UUID
    amo: ContactAmoSchema
    contact: ContactMainSchema
    cv: ContactCVSchema
    fpn: ContactFpnSchema
    fsa: ContactFsaSchema
    fxa: ContactFxaSchema
    newsletters: List[str]
    status: str = "ok"


class IdentityResponse(BaseModel):
    """The identity keys for a contact."""

    id: Optional[str] = None
    amo_id: Optional[str] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[str] = None
    token: Optional[str] = None
