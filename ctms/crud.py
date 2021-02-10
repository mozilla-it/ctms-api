from uuid import UUID

from sqlalchemy.orm import Session

from .models import Email
from .schemas import (
    ContactSchema,
    EmailSchema,
    FirefoxAccountsSchema,
    VpnWaitlistSchema,
)


def get_email_by_email_id(db: Session, email_id: UUID):
    return db.query(Email).filter(Email.email_id == email_id).first()


def create_email(db: Session, email: EmailSchema):
    db_email = Email(**email.dict())
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email
