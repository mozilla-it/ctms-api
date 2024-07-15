from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import UUID4, AnyUrl, ConfigDict, Field

from .base import ComparableBase
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE

if TYPE_CHECKING:
    from ctms.models import Newsletter


class NewsletterBase(ComparableBase):
    """The newsletter subscriptions schema."""

    name: str = Field(
        description="Basket slug for the newsletter",
        examples=["mozilla-welcome"],
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
        max_length=5,
        description="Newsletter language code, usually 2 lowercase letters",
    )
    source: Optional[AnyUrl] = Field(
        default=None,
        description="Source URL of subscription",
        examples=["https://www.mozilla.org/en-US/"],
    )
    unsub_reason: Optional[str] = Field(
        default=None, description="Reason for unsubscribing"
    )

    def __lt__(self, other):
        return self.name < other.name

    model_config = ConfigDict(from_attributes=True)


# No need to change anything, just extend if you want to
NewsletterInSchema = NewsletterBase
NewsletterSchema = NewsletterBase


class NewsletterTimestampedSchema(NewsletterBase):
    create_timestamp: datetime = Field(
        description="Newsletter data creation timestamp",
        examples=["2020-12-05T19:21:50.908000+00:00"],
    )
    update_timestamp: datetime = Field(
        description="Newsletter data update timestamp",
        examples=["2021-02-04T15:36:57.511000+00:00"],
    )


class NewsletterTableSchema(NewsletterTimestampedSchema):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        examples=[EMAIL_ID_EXAMPLE],
    )
    model_config = ConfigDict(extra="forbid")
