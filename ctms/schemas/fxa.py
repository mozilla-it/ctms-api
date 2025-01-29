from datetime import UTC, datetime

from pydantic import ConfigDict, Field

from .base import ComparableBase
from .common import ZeroOffsetDatetime


class FirefoxAccountsBase(ComparableBase):
    """The Firefox Account schema."""

    fxa_id: str | None = Field(
        default=None,
        description="Firefox Accounts foreign ID, FxA_Id__c in Salesforce",
        max_length=50,
        examples=["6eb6ed6ac3b64259968aa490c6c0b9df"],  # pragma: allowlist secret
    )
    primary_email: str | None = Field(
        default=None,
        description="FxA Email, can be foreign ID, FxA_Primary_Email__c in Salesforce",
        examples=["my-fxa-acct@example.com"],
    )
    created_date: str | None = Field(
        default=None,
        description="Source is unix timestamp, FxA_Created_Date__c in Salesforce",
        examples=["2021-01-29T18:43:49.082375+00:00"],
    )
    lang: str | None = Field(
        default=None,
        max_length=255,
        description="FxA Locale (from browser Accept-Language header), FxA_Language__c in Salesforce",
        examples=["en,en-US"],
    )
    first_service: str | None = Field(
        default=None,
        max_length=50,
        description="First service that an FxA user used, FirstService__c in Salesforce",
        examples=["sync"],
    )
    account_deleted: bool = Field(
        default=False,
        description="Set to True when FxA account deleted or dupe, FxA_Account_Deleted__c in Salesforce",
    )
    model_config = ConfigDict(from_attributes=True)


# No need to change anything, just extend if you want to
FirefoxAccountsInSchema = FirefoxAccountsBase
FirefoxAccountsSchema = FirefoxAccountsBase


class UpdatedFirefoxAccountsInSchema(FirefoxAccountsInSchema):
    update_timestamp: ZeroOffsetDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="FXA data update timestamp",
        examples=["2021-01-28T21:26:57.511+00:00"],
    )
