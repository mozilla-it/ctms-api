from typing import Optional

from pydantic import BaseModel


# TODO: Replace APIRequest with JSON Request Body fields
class APIRequest(BaseModel):
    pass


# TODO: Replace APIResponse with JSON Response Body fields
class APIResponse(BaseModel):
    pass


# TODO: Remove the Examples below ----
class ExampleAPIRequest(APIRequest):
    name: str  # Expected in the APIRequest
    type: Optional[str] = None  # Optional fields requires the '= None'


class ExampleAPIResponse(APIResponse):
    type: Optional[str] = None


# TODO: Remove the Examples above ----
