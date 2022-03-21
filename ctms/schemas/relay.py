from datetime import datetime, timezone
from typing import Optional

from pydantic import UUID4, Field

from .base import ComparableBase
from .email import EMAIL_ID_DESCRIPTION, EMAIL_ID_EXAMPLE


class RelayWaitlistBase(ComparableBase):
    """
    The Mozilla Relay Waitlist schema.

    """

    geo: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Relay waitlist country",
        example="fr",
    )

    class Config:
        orm_mode = True


# No need to change anything, just extend if you want to
RelayWaitlistInSchema = RelayWaitlistBase
RelayWaitlistSchema = RelayWaitlistBase


class UpdatedRelayWaitlistInSchema(RelayWaitlistInSchema):
    update_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Relay Waitlist data update timestamp",
        example="2021-01-28T21:26:57.511Z",
    )


class RelayWaitlistTableSchema(RelayWaitlistBase):
    email_id: UUID4 = Field(
        description=EMAIL_ID_DESCRIPTION,
        example=EMAIL_ID_EXAMPLE,
    )
    create_timestamp: datetime = Field(
        description="Relay Waitlist data creation timestamp",
        example="2020-12-05T19:21:50.908000+00:00",
    )
    update_timestamp: datetime = Field(
        description="Relay Waitlist data update timestamp",
        example="2021-02-04T15:36:57.511000+00:00",
    )

    class Config:
        extra = "forbid"
