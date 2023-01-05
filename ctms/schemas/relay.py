from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base import ComparableBase


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
