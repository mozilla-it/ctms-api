from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import UUID4, AnyUrl, Field

from .base import ComparableBase
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE

if TYPE_CHECKING:
    from ctms.models import Newsletter


class NewsletterBase(ComparableBase):
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
        max_length=5,
        description="Newsletter language code, usually 2 lowercase letters",
    )
    source: Optional[AnyUrl] = Field(
        default=None,
        description="Source URL of subscription",
        example="https://www.mozilla.org/en-US/",
    )
    unsub_reason: Optional[str] = Field(
        default=None, description="Reason for unsubscribing"
    )

    def __lt__(self, other):
        return self.name < other.name

    class Config:
        orm_mode = True


# No need to change anything, just extend if you want to
NewsletterInSchema = NewsletterBase
NewsletterSchema = NewsletterBase


class NewsletterTableSchema(NewsletterBase):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        example=EMAIL_ID_EXAMPLE,
    )
    create_timestamp: datetime = Field(
        description="Newsletter data creation timestamp",
        example="2020-12-05T19:21:50.908000+00:00",
    )
    update_timestamp: datetime = Field(
        description="Newsletter data update timestamp",
        example="2021-02-04T15:36:57.511000+00:00",
    )

    @classmethod
    def from_newsletter(cls, newsletter: "Newsletter") -> "NewsletterTableSchema":
        return cls(
            email_id=newsletter.email_id,
            name=newsletter.name,
            subscribed=newsletter.subscribed,
            format=newsletter.format,
            lang=newsletter.lang,
            source=newsletter.source,
            unsub_reason=newsletter.unsub_reason,
            create_timestamp=newsletter.create_timestamp,
            update_timestamp=newsletter.update_timestamp,
        )

    class Config:
        extra = "forbid"


class UpdatedNewsletterInSchema(NewsletterInSchema):
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Newsletter subscription data update timestamp",
        example="2021-01-28T21:26:57.511Z",
    )
