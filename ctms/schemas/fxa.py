from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class FirefoxAccountsBase(ComparableBase):
    """The Firefox Account schema."""

    fxa_id: Optional[str] = Field(
        default=None,
        description="Firefox Accounts foreign ID, FxA_Id__c in Salesforce",
        max_length=50,
        example="6eb6ed6ac3b64259968aa490c6c0b9df",  # pragma: allowlist secret
    )
    primary_email: Optional[str] = Field(
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
        max_length=255,
        description="FxA Locale (from browser Accept-Language header), FxA_Language__c in Salesforce",
        example="en,en-US",
    )
    first_service: Optional[str] = Field(
        default=None,
        max_length=50,
        description="First service that an FxA user used, FirstService__c in Salesforce",
        example="sync",
    )
    account_deleted: bool = Field(
        default=False,
        description=(
            "Set to True when FxA account deleted or dupe,"
            " FxA_Account_Deleted__c in Salesforce"
        ),
    )

    class Config:
        orm_mode = True


# No need to change anything, just extend if you want to
FirefoxAccountsInSchema = FirefoxAccountsBase
FirefoxAccountsSchema = FirefoxAccountsBase


class UpdatedFirefoxAccountsInSchema(FirefoxAccountsInSchema):
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="FXA data update timestamp",
        example="2021-01-28T21:26:57.511Z",
    )
