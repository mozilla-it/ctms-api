from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


# TODO: Replace APIRequest with JSON Request Body fields
class APIRequest(BaseModel):
    pass


# TODO: Replace APIResponse with JSON Response Body fields
class APIResponse(BaseModel):
    pass


# TODO: Remove the Examples below ----
class ExampleAPIRequest(APIRequest):
    name: str  # Expected in the APIRequest
    type: Optional[str] = None  # Optional fields requires the '= None'


class ExampleAPIResponse(APIResponse):
    type: Optional[str] = None


# TODO: Remove the Examples above ----


class UserIdentity(BaseModel):
    id: Optional[str] = None
    amo_id: Optional[str] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[str] = None
    token: Optional[str] = None


class UserMain(BaseModel):
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
    optin: Optional[str] = None
    optout: Optional[str] = None
    reason: Optional[str] = None
    record_type: Optional[str] = None
    id: Optional[str] = None


class UserSchema(BaseModel):
    amo_id: Optional[str] = None
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
    id: Optional[str] = None
    lang: Optional[str] = None
    last_modified_date: Optional[datetime] = None
    optin: Optional[bool] = None
    optout: Optional[bool] = None
    payee_id: Optional[str] = None
    postal_code: Optional[str] = None
    reason: Optional[str] = None
    record_type: Optional[str] = None
    token: Optional[str] = None
