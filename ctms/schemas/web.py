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


class TokenResponse(BaseModel):
    """An OAuth2 Token response."""

    access_token: str
    token_type: str
    expires_in: int


class UnauthorizedResponse(BaseModel):
    """Client authorization failed."""

    detail: str = Field(
        ...,
        description="A vague description of the authentication issue.",
        example="Not authenticated",
    )
