import base64
from datetime import datetime, timezone
from typing import Literal, Optional, Union

from pydantic import ConstrainedInt, conint, validator

from .base import ComparableBase

BLANK_VALS = [None, ""]

ConstrainedLimit: ConstrainedInt = conint(gt=0, le=100)
# Known issue with MyPy and constrained types
#   https://github.com/samuelcolvin/pydantic/issues/156


class BulkRequestSchema(ComparableBase):
    """A Bulk Read Request."""

    start_time: datetime

    end_time: Optional[Union[datetime, Literal[""]]] = None

    @validator("end_time", always=True)
    def end_time_must_not_be_blank(cls, value):  # pylint: disable=no-self-argument
        if value in BLANK_VALS:
            return datetime.now(timezone.utc)
        return value

    limit: Optional[Union[ConstrainedLimit, Literal[""]]] = 10

    @validator("limit", always=True)
    def limit_must_not_be_blank(cls, value):  # pylint: disable=no-self-argument
        if value in BLANK_VALS:
            return 10  # Default
        return value

    mofo_relevant: Optional[Union[bool, Literal[""]]] = None

    @validator("mofo_relevant", always=True)
    def mofo_relevant_must_not_be_blank(cls, value):  # pylint: disable=no-self-argument
        if value in BLANK_VALS:
            return None  # Default
        return value

    after: Optional[str] = None

    @validator("after", always=True)
    def after_must_be_base64_decodable(cls, value):  # pylint: disable=no-self-argument
        if value in BLANK_VALS:
            return None  # Default
        try:
            str_decode = base64.urlsafe_b64decode(value)
            str(str_decode.decode("utf-8")).split(
                ","
            )  # 'after' should be decodable otherwise err and invalid
            return value
        except Exception as e:
            raise ValueError(
                "'after' param validation error when decoding value."
            ) from e
