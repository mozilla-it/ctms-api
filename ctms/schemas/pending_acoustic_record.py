from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import ComparableBase


class PendingAcousticRecordBase(ComparableBase):
    """Data that is included in input/output/db of a pending_acoustic_record and such."""

    retry: int = Field(
        default=0,
        description="Set to the retry attempt.",
    )
    created_date: Optional[str] = Field(
        default=None,
        description="ISO 8601 Timestamp with utc",
        example="2021-01-29T18:43:49.082375+00:00",
    )

    update_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="ISO 8601 Timestamp with utc",
        example="2021-01-29T18:43:49.082375+00:00",
    )

    class Config:
        orm_mode = True


PendingAcousticRecordSchema = PendingAcousticRecordBase
PendingAcousticRecordInSchema = PendingAcousticRecordBase
