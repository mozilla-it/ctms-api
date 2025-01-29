from typing import Literal

from pydantic import UUID4, ConfigDict, Field

from .base import ComparableBase
from .common import AnyUrlString, ZeroOffsetDatetime
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE


class NewsletterBase(ComparableBase):
    """The newsletter subscriptions schema."""

    name: str = Field(
        description="Basket slug for the newsletter",
        examples=["mozilla-welcome"],
    )
    subscribed: bool = Field(default=True, description="True if subscribed, False when formerly subscribed")
    format: Literal["H", "T"] = Field(default="H", description="Newsletter format, H=HTML, T=Plain Text")
    lang: str | None = Field(
        default="en",
        min_length=2,
        max_length=5,
        description="Newsletter language code, usually 2 lowercase letters",
    )
    source: AnyUrlString | None = Field(
        default=None,
        description="Source URL of subscription",
        examples=["https://www.mozilla.org/en-US/"],
    )
    unsub_reason: str | None = Field(default=None, description="Reason for unsubscribing")

    def __lt__(self, other):
        return self.name < other.name

    model_config = ConfigDict(from_attributes=True)


# No need to change anything, just extend if you want to
NewsletterInSchema = NewsletterBase
NewsletterSchema = NewsletterBase


class NewsletterTimestampedSchema(NewsletterBase):
    create_timestamp: ZeroOffsetDatetime = Field(
        description="Newsletter data creation timestamp",
        examples=["2020-12-05T19:21:50.908000+00:00"],
    )
    update_timestamp: ZeroOffsetDatetime = Field(
        description="Newsletter data update timestamp",
        examples=["2021-02-04T15:36:57.511000+00:00"],
    )


class NewsletterTableSchema(NewsletterTimestampedSchema):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        examples=[EMAIL_ID_EXAMPLE],
    )
    model_config = ConfigDict(extra="forbid")
