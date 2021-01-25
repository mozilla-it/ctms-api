from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, EmailStr, uuid


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

class UserSchema(BaseModel):
    amo_id: Optional[Str] = None
    country: Optional[Str] = None
    created_date: Optional[datetime] = None
    cv_created_at: Optional[datetime] = None
    cv_days_interval: Optional[Str] = None
    cv_first_contribution_date: Optional[datetime] = None
    cv_goal_reached_at: Optional[Str] = None
    cv_last_active_date: Optional[Str] = None
    cv_two_day_streak: Optional[Str] = None
    email: Optional[EmailStr] = None
    fxa_id: Optional[Str] = None
    fxa_primary_email: Optional[Str] = None
    id: Optional[Str] = None
    lang: Optional[Str] = None
    last_modified_date: Optional[datetime] = None
    optin: Optional[Str] = None
    optout: Optional[Str] = None
    payee_id: Optional[Str] = None
    postal_code: Optional[Str] = None
    reason: Optional[Str] = None
    record_type: Optional[Str] = None
    token: Optional[Str] = None
        
class UserDict(BaseModel):
    user_dict: Dict[uuid.UUID, UserSchema]
