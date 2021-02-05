from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import UUID4, BaseModel, EmailStr, Field, HttpUrl


class ContactSchema(BaseModel):
    """A complete contact."""

    amo: Optional["ContactAddonsSchema"] = None
    email: Optional["ContactMainSchema"] = None
    cv: Optional["ContactCommonVoiceSchema"] = None
    fpn: Optional["ContactFirefoxPrivateNetworkSchema"] = None
    fsa: Optional["ContactFirefoxStudentAmbassadorSchema"] = None
    fxa: Optional["ContactFirefoxAccountsSchema"] = None
    newsletters: List[str] = []

    def as_identity_response(self) -> "IdentityResponse":
        """Return the identities of a contact"""
        return IdentityResponse(
            id=getattr(self.email, "id", None),
            email_id=self.email.email_id,
            amo_id=getattr(self.amo, "id", None),
            fxa_id=getattr(self.fxa, "id", None),
            fxa_primary_email=getattr(self.fxa, "primary_email", None),
            token=getattr(self.email, "token", None),
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


class SourceUrl(HttpUrl):
    max_length = 255


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
    email_id: UUID4 = Field(default_factory=uuid4, description="ID for email")
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
        max_length=1000,
        description="Reason for unsubscribing, in basket IGNORE_USER_FIELDS, Unsubscribe_Reason__c in Salesforce",
    )
    record_type: Optional[str] = Field(
        default=None,
        description="Salesforce record type, may be used to identify Foundation contacts, RecordTypeId in Salesforce",
    )
    source_url: Optional[SourceUrl] = Field(
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
                "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
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
    """
    The Firefox Private Network schema.

    These fields are present in Basket but might not be in SFDC.
    Requested in https://github.com/mozmeao/basket/issues/384
    """

    country: Optional[str] = Field(
        default=None,
        max_length=120,
        description="FPN waitlist country, FPN_Waitlist_Geo__c in Salesforce",
    )
    platform: Optional[str] = Field(
        default=None,
        max_length=120,
        description="FPRM waitlist, FPN_Waitlist_Platform__c in Salesforce",
    )

    class Config:
        schema_extra = {
            "example": {
                "country": "France",
                "platform": "Chrome",
            }
        }


class ContactFirefoxStudentAmbassadorSchema(BaseModel):
    """
    The Firefox Student Ambassador program schema

    This is now at https://community.mozilla.org/en/, may not be used.
    All fields are on basket's IGNORE_USER_FIELDS list, and are
    not planned to migrate to Acoustic.
    """

    allow_share: Optional[bool] = Field(
        default=None, description="FSA_Allow_Info_Shared__c in Salesforce"
    )
    city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="MailingCity or maybe FSA_City__c in Salesforce",
    )
    current_status: Optional[str] = Field(
        default=None, description="FSA_Current_Status__c in Salesforce"
    )
    grad_year: Optional[int] = Field(
        default=None, description="FSA_Grad_Year__c in Salesforce"
    )
    major: Optional[str] = Field(
        default=None, max_length=100, description="FSA_Major__c in Salesforce"
    )
    school: Optional[str] = Field(
        default=None, max_length=100, description="FSA_School__c in Salesforce"
    )

    class Config:
        schema_extra = {
            "example": {
                "allow_share": True,
                "city": "Dehradun",
                "current_status": "Student",
                "grad_year": 2012,
                "major": "Computer Science",
                "school": "DIT University, Makkawala, Salon gaon, Dehradun",
            }
        }


class ContactFirefoxAccountsSchema(BaseModel):
    """The Firefox Account schema."""

    create_date: Optional[datetime] = Field(
        default=None,
        description="Source is unix timestamp, FxA_Created_Date__c in Salesforce",
    )
    deleted: Optional[bool] = Field(
        default=None,
        description=(
            "Set to True when FxA account deleted or dupe,"
            " FxA_Account_Deleted__c in Salesforce"
        ),
    )
    id: Optional[str] = Field(
        default=None, description="Firefox Accounts foreign ID, FxA_Id__c in Salesforce"
    )
    lang: Optional[str] = Field(
        default=None,
        description="FxA Locale like 'en,en-US', FxA_Language__c in Salesforce",
    )
    primary_email: Optional[str] = Field(
        default=None,
        description="FxA Email, can be foreign ID, FxA_Primary_Email__c in Salesforce",
    )
    service: Optional[str] = Field(
        default=None,
        description="First service that an FxA user used, FirstService__c in Salesforce",
    )

    class Config:
        schema_extra = {
            "example": {
                "create_date": "2021-01-29T18:43:49.082375+00:00",
                "deleted": None,
                "id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
                "lang": "en,en-US",
                "primary_email": "my-fxa-acct@example.com",
                "service": "sync",
            }
        }


ContactSchema.update_forward_refs()


class CTMSResponse(BaseModel):
    """ContactSchema but sub-schemas are required."""

    amo: ContactAddonsSchema
    email: ContactMainSchema
    cv: ContactCommonVoiceSchema
    fpn: ContactFirefoxPrivateNetworkSchema
    fsa: ContactFirefoxStudentAmbassadorSchema
    fxa: ContactFirefoxAccountsSchema
    newsletters: List[str] = Field(
        default=[],
        description="List of identifiers for newsletters for which the contact is subscribed",
        example=(["firefox-welcome", "mozilla-welcome"]),
    )
    status: Literal["ok"] = Field(
        default="ok", description="Request was successful", example="ok"
    )


class IdentityResponse(BaseModel):
    """The identity keys for a contact."""

    email_id: UUID
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
