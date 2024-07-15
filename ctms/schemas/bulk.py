import base64
from datetime import datetime, timezone
from typing import Literal, Optional, Tuple, Union

import dateutil.parser
from pydantic import validator

from .base import ComparableBase

BLANK_VALS = [None, ""]


class BulkRequestSchema(ComparableBase):
    """A Bulk Read Request."""

    start_time: datetime

    end_time: Optional[Union[datetime, Literal[""]]] = None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("end_time", always=True)
    def end_time_must_not_be_blank(cls, value):  # pylint: disable=no-self-argument
        if value in BLANK_VALS:
            return datetime.now(timezone.utc)
        return value

    limit: Optional[Union[int, Literal[""]]] = None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("limit", always=True)
    def limit_must_adhere_to_validations(
        cls, value
    ):  # pylint: disable=no-self-argument
        if value in BLANK_VALS:
            return 100  # Default
        if value < 0:
            raise ValueError('"limit" should be greater than 0')
        if value > 1000:
            raise ValueError('"limit" should be less than or equal to 1000')
        return value

    mofo_relevant: Optional[Union[bool, Literal[""]]] = None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("mofo_relevant", always=True)
    def mofo_relevant_must_not_be_blank(cls, value):  # pylint: disable=no-self-argument
        if value in BLANK_VALS:
            return None  # Default
        return value

    after: Optional[str] = None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("after", always=True)
    def after_must_be_base64_decodable(cls, value):  # pylint: disable=no-self-argument
        if value in BLANK_VALS:
            return None  # Default
        try:
            str_decode = base64.urlsafe_b64decode(value)
            return str(
                str_decode.decode("utf-8")
            )  # 'after' should be decodable otherwise err and invalid
        except Exception as e:
            raise ValueError(
                "'after' param validation error when decoding value."
            ) from e

    @staticmethod
    def extractor_for_bulk_encoded_details(after: str) -> Tuple[str, datetime]:
        result_after_list = after.split(",")
        after_email_id = result_after_list[0]
        after_start_time = dateutil.parser.parse(result_after_list[1])
        return after_email_id, after_start_time

    @staticmethod
    def compressor_for_bulk_encoded_details(last_email_id, last_update_time):
        result_after_encoded = base64.urlsafe_b64encode(
            f"{last_email_id},{last_update_time}".encode("utf-8")
        )
        return result_after_encoded.decode()
