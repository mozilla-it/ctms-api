from uuid import UUID

from sqlalchemy.orm import Session

from .models import Email
from .schemas import (
    ContactAddonsSchema,
    ContactFirefoxAccountsSchema,
    ContactFirefoxPrivateNetworkSchema,
    ContactSchema,
    EmailSchema,
)


def get_contact_by_email_id(db: Session, email_id: UUID):
    return db.query(Email).filter(Email.email_id == email_id).first()


def get_contact_by_primary_email(db: Session, primary_email: str):
    return db.query(Email).filter(Email.primary_email == primary_email).first()
