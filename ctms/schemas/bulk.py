import base64
from datetime import datetime, timezone
from typing import Literal, Optional, Union

from pydantic import validator

from .base import ComparableBase

BLANK_VALS = [None, "", "null"]  # TODO: Should "null" be allowed?


class BulkRequestSchema(ComparableBase):
    """A Bulk Read Request."""

    start_time: datetime

    end_time: Optional[Union[datetime, Literal[""]]] = None

    @validator("end_time")
    def end_must_not_be_blank(self, value):
        if value in BLANK_VALS:
            return datetime.now(timezone.utc)
        return value

    limit: Optional[Union[int, Literal[""]]] = 10

    @validator("limit")
    def limit_must_not_be_blank(self, value):
        if value in BLANK_VALS:
            return 10
        return value

    mofo_relevant: Optional[Union[bool, Literal[""]]] = None

    @validator("mofo_relevant")
    def mofo_relevant_must_not_be_blank(self, value):
        if value in BLANK_VALS:
            return None
        return value

    after: Optional[str] = None

    @validator("after")
    def after_must_be_base64_decodable(self, value):
        if value in BLANK_VALS:
            return None
        try:
            str_decode = base64.urlsafe_b64decode(value)
            str(str_decode.decode("utf-8")).split(
                ","
            )  # 'after' should be decodable otherwise err and invalid
            return value
        except Exception as e:
            raise ValueError("'after' param validation error.") from e
