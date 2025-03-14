from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import UUID4, ConfigDict, Field, field_validator

from .base import ComparableBase
from .common import ZeroOffsetDatetime

EMAIL_ID_DESCRIPTION = "ID for email"
EMAIL_ID_EXAMPLE = "332de237-cab7-4461-bcc3-48e68f42bd5c"


class EmailBase(ComparableBase):
    """Data that is included in input/output/db of a primary_email and such."""

    primary_email: str = Field(
        description="Contact email address, Email in Salesforce",
        examples=["contact@example.com"],
    )
    basket_token: UUID | None = Field(
        default=None,
        description="Basket token, Token__c in Salesforce",
        examples=["c4a7d759-bb52-457b-896b-90f1d3ef8433"],
    )
    double_opt_in: bool = Field(
        default=False,
        description="User has clicked a confirmation link",
        examples=[True],
    )
    sfdc_id: str | None = Field(
        default=None,
        max_length=255,
        description="Salesforce legacy ID, Id in Salesforce",
        examples=["001A000023aABcDEFG"],
    )
    first_name: str | None = Field(
        default=None,
        max_length=255,
        description="First name of contact, FirstName in Salesforce",
        examples=["Jane"],
    )
    last_name: str | None = Field(
        default=None,
        max_length=255,
        description="Last name of contact, LastName in Salesforce",
        examples=["Doe"],
    )
    mailing_country: str | None = Field(
        default=None,
        max_length=255,
        description="Mailing country code, 2 lowercase letters, MailingCountryCode in Salesforce",
        examples=["us"],
    )
    email_format: Literal["H", "T", "N", ""] = Field(
        default="H",
        description="Email format, H=HTML, T=Plain Text, N and Empty=No selection, Email_Format__c in Salesforce",
    )
    email_lang: str | None = Field(
        default="en",
        max_length=5,
        description="Email language code, usually 2 lowercase letters, Email_Language__c in Salesforce",
    )
    has_opted_out_of_email: bool = Field(
        default=False,
        description="User has opted-out, HasOptedOutOfEmail in Salesforce",
    )
    unsubscribe_reason: str | None = Field(
        default=None,
        description="Reason for unsubscribing, in basket IGNORE_USER_FIELDS, Unsubscribe_Reason__c in Salesforce",
    )
    model_config = ConfigDict(from_attributes=True)


class EmailSchema(EmailBase):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        examples=[EMAIL_ID_EXAMPLE],
    )
    create_timestamp: ZeroOffsetDatetime | None = Field(
        default=None,
        description="Contact creation date, CreatedDate in Salesforce",
        examples=["2020-03-28T15:41:00.000+00:00"],
    )
    update_timestamp: ZeroOffsetDatetime | None = Field(
        default=None,
        description="Contact last modified date, LastModifiedDate in Salesforce",
        examples=["2021-01-28T21:26:57.511+00:00"],
    )


class EmailInSchema(EmailBase):
    """Nearly identical to EmailPutSchema but the email_id is not required."""

    email_id: UUID4 | None = Field(
        default=None,
        description=EMAIL_ID_DESCRIPTION,
        examples=[EMAIL_ID_EXAMPLE],
    )


class EmailPutSchema(EmailBase):
    """Nearly identical to EmailInSchema but the email_id is required."""

    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        examples=[EMAIL_ID_EXAMPLE],
    )


class EmailPatchSchema(EmailInSchema):
    """Nearly identical to EmailInSchema but nothing is required."""

    primary_email: str | None = None

    @field_validator("primary_email")
    @classmethod
    @classmethod
    def prevent_none(cls, value):
        assert value is not None, "primary_email may not be None"
        return value


class UpdatedEmailPutSchema(EmailPutSchema):
    update_timestamp: ZeroOffsetDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Contact last modified date, LastModifiedDate in Salesforce",
        examples=["2021-01-28T21:26:57.511+00:00"],
    )
