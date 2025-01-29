import base64
from datetime import UTC, datetime
from typing import Literal

import dateutil.parser
from pydantic import Field, field_validator

from .base import ComparableBase

BLANK_VALS = [None, ""]


class BulkRequestSchema(ComparableBase):
    """A Bulk Read Request."""

    start_time: datetime

    end_time: datetime | Literal[""] | None = Field(default=None, validate_default=True)

    @field_validator("end_time", mode="before")
    @classmethod
    def end_time_must_not_be_blank(cls, value):
        if value in BLANK_VALS:
            return datetime.now(UTC)
        return value

    limit: int | Literal[""] | None = Field(default=None, validate_default=True)

    @field_validator("limit", mode="before")
    @classmethod
    def limit_must_adhere_to_validations(cls, value):
        if value in BLANK_VALS:
            return 100  # Default
        if value < 0:
            raise ValueError('"limit" should be greater than 0')
        if value > 1000:
            raise ValueError('"limit" should be less than or equal to 1000')
        return value

    mofo_relevant: bool | Literal[""] | None = Field(default=None, validate_default=True)

    @field_validator("mofo_relevant", mode="before")
    @classmethod
    def mofo_relevant_must_not_be_blank(cls, value):
        if value in BLANK_VALS:
            return None  # Default
        return value

    after: str | None = Field(default=None, validate_default=True)

    @field_validator("after", mode="before")
    def after_must_be_base64_decodable(cls, value):
        if value in BLANK_VALS:
            return None  # Default
        try:
            str_decode = base64.urlsafe_b64decode(value)
            return str(str_decode.decode("utf-8"))  # 'after' should be decodable otherwise err and invalid
        except Exception as e:
            raise ValueError("'after' param validation error when decoding value.") from e

    @staticmethod
    def extractor_for_bulk_encoded_details(after: str) -> tuple[str, datetime]:
        result_after_list = after.split(",")
        after_email_id = result_after_list[0]
        after_start_time = dateutil.parser.parse(result_after_list[1])
        return after_email_id, after_start_time

    @staticmethod
    def compressor_for_bulk_encoded_details(last_email_id, last_update_time):
        result_after_encoded = base64.urlsafe_b64encode(f"{last_email_id},{last_update_time}".encode())
        return result_after_encoded.decode()
