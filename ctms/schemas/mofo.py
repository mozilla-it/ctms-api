from typing import Optional

from pydantic import Field

from .base import ComparableBase


class MozillaFoundationBase(ComparableBase):
    mofo_email_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Foriegn key to email in MoFo contact database",
    )
    mofo_contact_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Foriegn key to contact in MoFo contact database",
    )
    mofo_relevant: bool = Field(
        default=False, description="Mozilla Foundation is tracking this email"
    )

    class Config:
        orm_mode = True


MozillaFoundationSchema = MozillaFoundationBase
MozillaFoundationInSchema = MozillaFoundationBase
