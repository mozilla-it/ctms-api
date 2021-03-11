from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import UUID4, EmailStr, Field, HttpUrl

from .base import ComparableBase


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
    source: Optional[HttpUrl] = Field(
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
