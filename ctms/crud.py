from sqlalchemy.orm import Session

from . import models, schemas


def get_email_by_primary_email(db: Session, primary_email: str):
    return (
        db.query(models.Email)
        .filter(models.Email.primary_email == primary_email)
        .first()
    )
