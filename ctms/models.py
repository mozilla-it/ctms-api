from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class ContactSchema(BaseModel):
    """A complete contact."""

    id: UUID
    amo: Optional["ContactAddonsSchema"] = None
    contact: Optional["ContactMainSchema"] = None
    cv: Optional["ContactCommonVoiceSchema"] = None
    fpn: Optional["ContactFirefoxPrivateNetworkSchema"] = None
    fsa: Optional["ContactFirefoxStudentAmbassadorSchema"] = None
    fxa: Optional["ContactFirefoxAccountsSchema"] = None
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


class ContactAddonsSchema(BaseModel):
    """
    The addons.mozilla.org (AMO) data for a contact.

    Extra info in Basket / Salesforce:
    * amo_deleted - True if the user was deleted in AMO. Basket also sets
        the amo_id to null on deletion.

    All are in basket's IGNORE_USER_FIELDS, and usually stripped from
    contact data on the return from Salesforce.
    """

    display_name: Optional[str] = Field(
        default=None,
        description="Author name on AMO, AMO_Display_Name__c in Salesforce",
    )
    homepage: Optional[str] = Field(
        default=None,
        description=(
            "Homepage linked on AMO, AMO_Location__c in Salesforce,"
            " <em>planning to drop</em>"
        ),
    )
    id: Optional[int] = Field(
        default=None, description="Author ID on AMO, AMO_User_ID__c in Salesforce"
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="Last login on addons.mozilla.org, AMO_Last_Login__c in Salesforce",
    )
    location: Optional[str] = Field(
        default=None,
        description="Free-text location on AMO, AMO_Location__c in Salesforce",
    )
    user: bool = Field(
        default=False,
        description="True if user is from an Add-on sync, AMO_User__c in Salesforce",
    )

    class Config:
        schema_extra = {
            "example": {
                "display_name": "Add-ons Author",
                "homepage": "https://my-mozilla-addon.example.org/",
                "id": 98765,
                "last_login": "2021-01-28T19:21:50.908Z",
                "location": "California, USA, Earth",
                "user": True,
            }
        }


class ContactMainSchema(BaseModel):
    """The "main" contact schema."""

    country: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
        regex="^[a-z][a-z]$",
        description="Mailing country code, 2 lowercase letters, MailingCountryCode in Salesforce",
    )
    created_date: Optional[datetime] = Field(
        default=None, description="Contact creation date, CreatedDate in Salesforce"
    )
    email: Optional[EmailStr] = Field(
        default=None, description="Contact email address, Email in Salesforce"
    )
    first_name: Optional[str] = Field(
        default=None,
        max_length=40,
        description="First name of contact, FirstName in Salesforce",
    )
    format: Literal["H", "T"] = Field(
        default="H",
        description="Email format, H=HTML, T=Plain Text, Email_Format__c in Salesforce",
    )
    id: Optional[str] = Field(
        default=None, description="Salesforce record ID, Id in Salesforce"
    )
    lang: Optional[str] = Field(
        default="en",
        min_length=2,
        max_length=2,
        regex="^[a-z][a-z]$",
        description="Email language code, 2 lowercase letters, Email_Language__c in Salesforce",
    )
    last_modified_date: Optional[datetime] = Field(
        default=None,
        description="Contact last modified date, LastModifiedDate in Salesforce",
    )
    last_name: str = Field(
        default="_",
        max_length=80,
        description="Last name, '_' for blank, LastName in Salesforce",
    )
    optin: bool = Field(
        default=False,
        description="Double opt-in complete or skipped, Double_Opt_In__c in Salesforce",
    )
    optout: bool = Field(
        default=False,
        description="User has opted-out, HasOptedOutOfEmail in Salesforce",
    )
    payee_id: Optional[str] = Field(
        default=None,
        description="Payment system ID (Stripe or other), in basket IGNORE_USER_FIELDS, PMT_Cust_Id__c in Salesforce",
    )
    postal_code: Optional[str] = Field(
        default=None, description="Mailing postal code, MailingPostalCode in Salesforce"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for unsubscribing, in basket IGNORE_USER_FIELDS, Unsubscribe_Reason__c in Salesforce",
    )
    record_type: Optional[str] = Field(
        default=None,
        description="Salesforce record type, may be used to identify Foundation contacts, RecordTypeId in Salesforce",
    )
    source_url: Optional[HttpUrl] = Field(
        default=None,
        description="URL where the contact first signed up, Signup_Source_URL__c in Salesforce",
    )
    token: Optional[UUID] = Field(
        default=None, description="Basket token, Token__c in Salesforce"
    )

    class Config:
        schema_extra = {
            "example": {
                "country": "us",
                "created_date": "2020-03-28T15:41:00.000Z",
                "email": "contact@example.com",
                "first_name": None,
                "format": "H",
                "id": "001A000023aABcDEFG",
                "lang": "en",
                "last_modified_date": "2021-01-28T21:26:57.511Z",
                "last_name": "_",
                "optin": True,
                "optout": False,
                "payee_id": None,
                "postal_code": "94041",
                "reason": None,
                "record_type": "0124A0000001aABCDE",
                "source_url": "https://www.mozilla.org/en-US/",
                "token": "c4a7d759-bb52-457b-896b-90f1d3ef8433",
            }
        }


class ContactCommonVoiceSchema(BaseModel):
    """
    The CommonVoice schema.

    With the Jan 2021 adoption of the project by the Mozilla Foundation,
    this data may move out of CTMS.

    All of this data is in basket's IGNORE_USER_FIELDS, ignored by default
    when displaying or updating contact data.
    """

    created_at: Optional[datetime] = Field(
        default=None,
        description="Creation date of common voice account, cv_created_at__c in Salesforce",
    )
    days_interval: Optional[int] = Field(
        default=None, description="Unknown, cv_days_interval__c in Salesforce"
    )
    first_contribution_date: Optional[datetime] = Field(
        default=None,
        description="Date of first contribution, cv_days_interval__c in Salesforce",
    )
    goal_reached_at: Optional[datetime] = Field(
        default=None, description="Unknown, cv_goal_reached_at__c in Salesforce"
    )
    last_active_date: Optional[datetime] = Field(
        default=None,
        description="Last day the user was active on CV, cv_last_active_dt__c in Salesforce <em>(not on retain list)</em>",
    )
    two_day_streak: Optional[bool] = Field(
        default=None,
        description="Unknown, cv_two_day_streak in Salesforce <em>(not on retain list)</em>",
    )

    class Config:
        schema_extra = {
            "example": {
                "created_at": "2019-02-14T16:05:21.423Z",
                "days_interval": 10,
                "first_contribution_date": "2019-02-15T10:07Z",
                "goal_reached_at": "2019-03-15T11:15:19Z",
                "last_active_date": "2020-12-10T16:56Z",
                "two_day_streak": True,
            }
        }


class ContactFirefoxPrivateNetworkSchema(BaseModel):
    """The Firefox Private Network schema."""

    country: Optional[str] = None
    platform: Optional[str] = None


class ContactFirefoxStudentAmbassadorSchema(BaseModel):
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


class ContactFirefoxAccountsSchema(BaseModel):
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
    amo: ContactAddonsSchema
    contact: ContactMainSchema
    cv: ContactCommonVoiceSchema
    fpn: ContactFirefoxPrivateNetworkSchema
    fsa: ContactFirefoxStudentAmbassadorSchema
    fxa: ContactFirefoxAccountsSchema
    newsletters: List[str]
    status: Literal["ok"]


class IdentityResponse(BaseModel):
    """The identity keys for a contact."""

    id: Optional[str] = None
    amo_id: Optional[int] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[EmailStr] = None
    token: Optional[UUID] = None


class NotFoundResponse(BaseModel):
    """The content of the 404 Not Found message."""

    detail: str

    class Config:
        schema_extra = {"example": {"detail": "Unknown contact_id"}}
