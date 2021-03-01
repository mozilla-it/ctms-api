from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class BadRequestResponse(BaseModel):
    """The client called the endpoint incorrectly."""

    detail: str = Field(
        ...,
        description="A human-readable summary of the client error.",
        example="No identifiers provided, at least one is needed.",
    )


class NotFoundResponse(BaseModel):
    """No existing record was found for the indentifier."""

    detail: str = Field(
        ...,
        description="A human-readable summary of the issue.",
        example="Unknown contact_id",
    )
