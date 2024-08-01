from datetime import date, datetime, timezone
from typing import Optional

from pydantic import ConfigDict, Field

from .base import ComparableBase
from .common import ZeroOffsetDatetime


class AddOnsBase(ComparableBase):
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
        examples=["add-on-1,add-on-2"],
    )
    display_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Display name on AMO, AMO_Display_Name__c in Salesforce",
        examples=["Add-ons Author"],
    )
    email_opt_in: bool = Field(
        default=False,
        description="Account has opted into emails, AMO_Email_Opt_In__c in Salesforce",
    )
    language: Optional[str] = Field(
        default=None,
        max_length=5,
        description="Account language, AMO_Language__c in Salesforce",
        examples=["en"],
    )
    last_login: Optional[date] = Field(
        default=None,
        description="Last login date on addons.mozilla.org, AMO_Last_Login__c in Salesforce",
        examples=["2021-01-28"],
    )
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Free-text location on AMO, AMO_Location__c in Salesforce",
        examples=["California"],
    )
    profile_url: Optional[str] = Field(
        default=None,
        max_length=40,
        description="AMO profile URL, AMO_Profile_URL__c in Salesforce",
        examples=["firefox/user/98765"],
    )
    user: bool = Field(
        default=False,
        description="True if user is from an Add-on sync, AMO_User__c in Salesforce",
        examples=[True],
    )
    user_id: Optional[str] = Field(
        default=None,
        max_length=40,
        description="User ID on AMO, AMO_User_ID__c in Salesforce",
        examples=["98765"],
    )
    username: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Username on AMO, AMO_Username__c in Salesforce",
        examples=["AddOnAuthor"],
    )
    model_config = ConfigDict(from_attributes=True)


# No need to change anything, just extend if you want to
AddOnsInSchema = AddOnsBase


class UpdatedAddOnsInSchema(AddOnsInSchema):
    update_timestamp: ZeroOffsetDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="AMO data update timestamp",
        examples=["2021-01-28T21:26:57.511+00:00"],
    )


class AddOnsSchema(AddOnsBase):
    create_timestamp: Optional[ZeroOffsetDatetime] = Field(
        default=None,
        description="AMO data creation timestamp",
        examples=["2020-12-05T19:21:50.908000+00:00"],
    )
    update_timestamp: Optional[ZeroOffsetDatetime] = Field(
        default=None,
        description="AMO data update timestamp",
        examples=["2021-02-04T15:36:57.511000+00:00"],
    )
