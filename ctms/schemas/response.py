from pydantic import BaseModel, UUID4


class Response(BaseModel):
    status: str


class GDPRDeleteResponse(Response):
    dropped: list[dict[str, str | UUID4]]
