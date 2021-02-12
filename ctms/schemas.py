from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import UUID4, BaseModel, EmailStr, Field, HttpUrl


class ContactSchema(BaseModel):
    """A complete contact."""

    amo: Optional["AddOnsSchema"] = None
    email: "EmailSchema" = None
    fxa: Optional["FirefoxAccountsSchema"] = None
    newsletters: List["NewsletterSchema"] = Field(
        default=[],
        description="List of newsletters for which the contact is or was subscribed",
        example=([{"name": "firefox-welcome"}, {"name": "mozilla-welcome"}]),
    )
    vpn_waitlist: Optional["VpnWaitlistSchema"] = None

    def as_identity_response(self) -> "IdentityResponse":
        """Return the identities of a contact"""
        return IdentityResponse(
            amo_user_id=getattr(self.amo, "user_id", None),
            basket_token=getattr(self.email, "basket_token", None),
            email_id=getattr(self.email, "email_id", None),
            fxa_id=getattr(self.fxa, "fxa_id", None),
            fxa_primary_email=getattr(self.fxa, "primary_email", None),
            primary_email=getattr(self.email, "primary_email", None),
            sfdc_id=getattr(self.email, "sfdc_id", None),
        )


class AddOnsSchema(BaseModel):
    """
    The addons.mozilla.org (AMO) data for a contact.

    Extra info in Basket:
    * amo_deleted - True if the user was deleted in AMO. Basket also sets
        the amo_id to null on deletion.

    All are in basket's IGNORE_USER_FIELDS, and usually stripped from
    contact data on the return from Salesforce.
    """

    add_on_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated list of add-ons for account, AMO_Add_On_ID_s__c in Salesforce",
        example="add-on-1,add-on-2",
    )
    display_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Display name on AMO, AMO_Display_Name__c in Salesforce",
        example="Add-ons Author",
    )
    email_opt_in: bool = Field(
        default=False,
        description="Account has opted into emails, AMO_Email_Opt_In__c in Salesforce",
    )
    language: Optional[str] = Field(
        default=None,
        max_length=5,
        description="Account language, AMO_Language__c in Salesforce",
        example="en",
    )
    last_login: Optional[str] = Field(
        default=None,
        max_length=40,
        description="Last login on addons.mozilla.org, AMO_Last_Login__c in Salesforce",
        example="2021-01-28T19:21:50.908Z",
    )
    location: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Free-text location on AMO, AMO_Location__c in Salesforce",
        example="California",
    )
    profile_url: Optional[str] = Field(
        default=None,
        max_length=40,
        description="AMO profile URL, AMO_Profile_URL__c in Salesforce",
        example="firefox/user/98765",
    )
    user: bool = Field(
        default=False,
        description="True if user is from an Add-on sync, AMO_User__c in Salesforce",
        example=True,
    )
    user_id: Optional[str] = Field(
        default=None,
        max_length=40,
        description="User ID on AMO, AMO_User_ID__c in Salesforce",
        example="98765",
    )
    username: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Username on AMO, AMO_Username__c in Salesforce",
        example="AddOnAuthor",
    )
    create_timestamp: Optional[datetime] = Field(
        default=None,
        description="AMO data creation timestamp",
        example="2020-12-05T19:21:50.908000+00:00",
    )
    update_timestamp: Optional[datetime] = Field(
        default=None,
        description="AMO data update timestamp",
        example="2021-02-04T15:36:57.511000+00:00",
    )


class EmailSchema(BaseModel):
    """The primary email and related data."""

    email_id: UUID4 = Field(
        default_factory=uuid4,
        description="ID for email",
        example="332de237-cab7-4461-bcc3-48e68f42bd5c",
    )
    primary_email: EmailStr = Field(
        ...,
        description="Contact email address, Email in Salesforce",
        example="contact@example.com",
    )
    basket_token: Optional[UUID] = Field(
        ...,
        description="Basket token, Token__c in Salesforce",
        example="c4a7d759-bb52-457b-896b-90f1d3ef8433",
    )
    sfdc_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Salesforce legacy ID, Id in Salesforce",
        example="001A000023aABcDEFG",
    )
    first_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="First name of contact, FirstName in Salesforce",
        example="Jane",
    )
    last_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Last name of contact, LastName in Salesforce",
        example="Doe",
    )
    mailing_country: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Mailing country code, 2 lowercase letters, MailingCountryCode in Salesforce",
        example="us",
    )
    email_format: Literal["H", "T", "N", ""] = Field(
        default="H",
        description="Email format, H=HTML, T=Plain Text, N and Empty=No selection, Email_Format__c in Salesforce",
    )
    email_lang: Optional[str] = Field(
        default="en",
        max_length=2,
        description="Email language code, 2 lowercase letters, Email_Language__c in Salesforce",
    )
    mofo_relevant: bool = Field(
        default=False, description="Mozilla Foundation is tracking this email"
    )
    has_opted_out_of_email: bool = Field(
        default=False,
        description="User has opted-out, HasOptedOutOfEmail in Salesforce",
    )
    pmt_cust_id: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Payment system ID (Stripe or other), in basket IGNORE_USER_FIELDS, PMT_Cust_Id__c in Salesforce",
    )
    subscriber: bool = Field(
        default=False, description="TODO: add description. Subscriber__c in Salesforce"
    )
    unsubscribe_reason: Optional[str] = Field(
        default=None,
        description="Reason for unsubscribing, in basket IGNORE_USER_FIELDS, Unsubscribe_Reason__c in Salesforce",
    )
    create_timestamp: Optional[datetime] = Field(
        default=None,
        description="Contact creation date, CreatedDate in Salesforce",
        example="2020-03-28T15:41:00.000Z",
    )
    update_timestamp: Optional[datetime] = Field(
        default=None,
        description="Contact last modified date, LastModifiedDate in Salesforce",
        example="2021-01-28T21:26:57.511Z",
    )

    class Config:
        orm_mode = True


class VpnWaitlistSchema(BaseModel):
    """
    The Mozilla VPN Waitlist schema.

    This was previously the Firefox Private Network (fpn) waitlist data,
    with a similar purpose.
    """

    geo: Optional[str] = Field(
        default=None,
        max_length=100,
        description="VPN waitlist country, FPN_Waitlist_Geo__c in Salesforce",
        example="fr",
    )
    platform: Optional[str] = Field(
        default=None,
        max_length=100,
        description=(
            "VPN waitlist platforms as comma-separated list,"
            " FPN_Waitlist_Platform__c in Salesforce"
        ),
        example="ios,mac",
    )


class FirefoxAccountsSchema(BaseModel):
    """The Firefox Account schema."""

    fxa_id: Optional[str] = Field(
        default=None,
        description="Firefox Accounts foreign ID, FxA_Id__c in Salesforce",
        max_length=50,
        example="6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
    )
    primary_email: Optional[EmailStr] = Field(
        default=None,
        description="FxA Email, can be foreign ID, FxA_Primary_Email__c in Salesforce",
        example="my-fxa-acct@example.com",
    )
    created_date: Optional[str] = Field(
        default=None,
        description="Source is unix timestamp, FxA_Created_Date__c in Salesforce",
        example="2021-01-29T18:43:49.082375+00:00",
    )
    lang: Optional[str] = Field(
        default=None,
        max_length=10,
        description="FxA Locale, FxA_Language__c in Salesforce",
        example="en,en-US",
    )
    first_service: Optional[str] = Field(
        default=None,
        max_length=50,
        description="First service that an FxA user used, FirstService__c in Salesforce",
        example="sync",
    )
    deleted: bool = Field(
        default=False,
        description=(
            "Set to True when FxA account deleted or dupe,"
            " FxA_Account_Deleted__c in Salesforce"
        ),
    )


class NewsletterSchema(BaseModel):
    """The newsletter subscriptions schema."""

    name: str = Field(
        description="Basket slug for the newsletter",
        example="mozilla-welcome",
    )
    subscribed: bool = Field(
        default=True, description="True if subscribed, False when formerly subscribed"
    )
    format: Literal["H", "T"] = Field(
        default="H", description="Newsletter format, H=HTML, T=Plain Text"
    )
    lang: Optional[str] = Field(
        default="en",
        min_length=2,
        max_length=2,
        regex="^[a-z][a-z]$",
        description="Newsletter language code, 2 lowercase letters",
    )
    source: Optional[HttpUrl] = Field(
        default=None,
        description="Source URL of subscription",
        example="https://www.mozilla.org/en-US/",
    )
    unsub_reason: Optional[str] = Field(
        default=None, description="Reason for unsubscribing"
    )


ContactSchema.update_forward_refs()


class CTMSResponse(ContactSchema):
    """ContactSchema but sub-schemas are required."""

    amo: AddOnsSchema
    email: EmailSchema
    fxa: FirefoxAccountsSchema
    # newsletters - Default is already an empty list, no changes needed
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
    amo_user_id: Optional[str] = None
    fxa_id: Optional[str] = None
    fxa_primary_email: Optional[EmailStr] = None


class BadRequestResponse(BaseModel):
    """The client called the endpoint incorrectly."""

    detail: str = Field(
        ...,
        description="A human-readable summary of the client error.",
        example="No identifiers provided, at least one is needed.",
    )


class NotFoundResponse(BaseModel):
    """No existing record was found for the indentifier."""

    detail: str = Field(
        ...,
        description="A human-readable summary of the issue.",
        example="Unknown contact_id",
    )
