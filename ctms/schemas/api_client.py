from pydantic import BaseModel, EmailStr


class ApiClientSchema(BaseModel):
    """An OAuth2 Client"""

    client_id: str
    email: EmailStr
    enabled: bool
