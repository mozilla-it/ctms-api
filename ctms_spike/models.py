from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class ContactSchema(BaseModel):
    """A complete contact."""

    contact_id: UUID
    amo_data: Optional["ContactAmoSchema"] = None
    main_data: Optional["ContactMainSchema"] = None
    cv_data: Optional["ContactCVSchema"] = None
    fpn_data: Optional["ContactFpnSchema"] = None
    fsa_data: Optional["ContactFsaSchema"] = None
    fxa_data: Optional["ContactFxaSchema"] = None
    newsletters: List[str] = []

    def as_ctms_response(self) -> "CTMSResponse":
        """Return the flat version of a contact"""
        items: Dict[str, Any] = {}
        items.update(self.amo_data or {})
        items.update(self.main_data or {})
        items.update(self.cv_data or {})
        items.update(self.fpn_data or {})
        items.update(self.fsa_data or {})
        items.update(self.fxa_data or {})
        items["newsletters"] = self.newsletters or []
        response = CTMSResponse(**items)
        return response

    def as_identity_response(self) -> "IdentityResponse":
        """Return the identities of a contact"""
        return IdentityResponse(
            id=getattr(self.main_data, "id", None),
            amo_id=getattr(self.amo_data, "amo_id", None),
            fxa_id=getattr(self.fxa_data, "fxa_id", None),
            fxa_primary_email=getattr(self.fxa_data, "fxa_primary_email", None),
            token=getattr(self.main_data, "token", None),
        )


class ContactAmoSchema(BaseModel):
    """
    The addons.mozilla.org data for a contact.

    TODO: Decide if we keep all the "amo_" prefixes
    TODO: amo_user: When is this set true?
    - upsert_amo_user_data - set to True when User Sync request
      https://github.com/mozmeao/basket/blob/31941961e56c462a7d260f079c937e05ac0d9ae3/basket/news/tasks.py#L1137
    - amo_check_user_for_deletion - set to False when deleting a user
      https://github.com/mozmeao/basket/blob/31941961e56c462a7d260f079c937e05ac0d9ae3/basket/news/tasks.py#L1189
    """

    amo_id: Optional[str] = None
    amo_display_name: Optional[str] = None
    amo_homepage: Optional[str] = None
    amo_last_login: Optional[datetime] = None
    amo_location: Optional[str] = None
    amo_user: bool = False


class ContactMainSchema(BaseModel):
    """
    The "main" schema

    TODO: Do cv_ fields belong in here? Are the Common Voice?
    """

    postal_code: Optional[str] = None
    cv_created_at: Optional[datetime] = None
    cv_days_interval: Optional[str] = None
    cv_first_contribution_date: Optional[datetime] = None
    cv_goal_reached_at: Optional[str] = None
    cv_last_active_date: Optional[str] = None
    cv_two_day_streak: Optional[str] = None
    email: Optional[EmailStr] = None
    token: Optional[str] = None
    country: Optional[str] = None
    created_date: Optional[datetime] = None
    lang: Optional[str] = None
    last_modified_date: Optional[datetime] = None
    optin: Optional[bool] = None
    optout: Optional[bool] = None
    reason: Optional[str] = None
    record_type: Optional[str] = None
    id: Optional[str] = None


class ContactCVSchema(BaseModel):
    """
    The CommonVoice Schema?

    TODO: What does CV stand for?
    """

    source_url: Optional[str] = None
    format: Optional[str] = None
    payee_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ContactFpnSchema(BaseModel):
    """
    The Firefox Private Network schema?

    TODO: What does FPN stand for?
    """

    fpn_country: Optional[str] = None
    fpn_platform: Optional[str] = None


class ContactFsaSchema(BaseModel):
    """
    The internship program schema?

    TODO: What does FSA stand for?
    TODO: Keep fsa_ prefix?
    """

    fsa_allow_share: Optional[str] = None
    fsa_city: Optional[str] = None
    fsa_current_status: Optional[str] = None
    fsa_grad_year: Optional[int] = None
    fsa_major: Optional[str] = None
    fsa_school: Optional[str] = None


class ContactFxaSchema(BaseModel):
    """
    The Firefox Account schema
    TODO: Keep fxa_ prefix?
    """

    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[str] = None
    fxa_create_date: Optional[datetime] = None
    fxa_deleted: Optional[bool] = None
    fxa_lang: Optional[str] = None
    fxa_service: Optional[str] = None


ContactSchema.update_forward_refs()


class CTMSResponse(BaseModel):
    """A flatter contact schema for the /ctms/ endpoint."""

    amo_id: Optional[str] = None
    amo_display_name: Optional[str] = None
    amo_homepage: Optional[str] = None
    amo_last_login: Optional[datetime] = None
    amo_location: Optional[str] = None
    amo_user: bool = False
    country: Optional[str] = None
    created_date: Optional[datetime] = None
    cv_created_at: Optional[datetime] = None
    cv_days_interval: Optional[str] = None
    cv_first_contribution_date: Optional[datetime] = None
    cv_goal_reached_at: Optional[str] = None
    cv_last_active_date: Optional[str] = None
    cv_two_day_streak: Optional[str] = None
    email: Optional[EmailStr] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[str] = None
    fxa_create_date: Optional[datetime] = None
    fxa_deleted: Optional[bool] = None
    fxa_lang: Optional[str] = None
    fxa_service: Optional[str] = None
    id: Optional[str] = None
    lang: Optional[str] = None
    last_modified_date: Optional[datetime] = None
    optin: Optional[bool] = None
    optout: Optional[bool] = None
    postal_code: Optional[str] = None
    reason: Optional[str] = None
    record_type: Optional[str] = None
    token: Optional[str] = None
    source_url: Optional[str] = None
    format: Optional[str] = None
    payee_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    fpn_country: Optional[str] = None
    fpn_platform: Optional[str] = None
    fsa_allow_share: Optional[str] = None
    fsa_city: Optional[str] = None
    fsa_current_status: Optional[str] = None
    fsa_grad_year: Optional[int] = None
    fsa_major: Optional[str] = None
    fsa_school: Optional[str] = None
    status: str = "ok"
    newsletters: List[str] = []


class IdentityResponse(BaseModel):
    """The identity keys for a contact."""

    id: Optional[str] = None
    amo_id: Optional[str] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[str] = None
    token: Optional[str] = None


class ContactCVResponse(ContactCVSchema):
    """
    The CommonVoice? GET response

    Borrows the ID from the Contact's main data
    """

    id: Optional[str] = None
