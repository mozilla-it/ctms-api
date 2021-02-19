from uuid import UUID

from sqlalchemy.orm import Session

from .models import AmoAccount, Email, FirefoxAccount, Newsletter, VpnWaitlist
from .schemas import (
    AddOnsSchema,
    ContactSchema,
    EmailSchema,
    FirefoxAccountsSchema,
    NewsletterSchema,
    VpnWaitlistSchema,
)


def get_email_by_email_id(db: Session, email_id: UUID):
    return db.query(Email).filter(Email.email_id == email_id).first()


def get_contact_by_email_id(db: Session, email_id: UUID):
    """Get all the data for a contact."""
    result = (
        db.query(Email, AmoAccount, FirefoxAccount, VpnWaitlist)
        .outerjoin(AmoAccount, Email.email_id == AmoAccount.email_id)
        .outerjoin(FirefoxAccount, Email.email_id == FirefoxAccount.email_id)
        .outerjoin(VpnWaitlist, Email.email_id == VpnWaitlist.email_id)
        .filter(Email.email_id == email_id)
        .first()
    )
    if result is None:
        return None
    email, amo, fxa, vpn_waitlist = result
    newsletters = db.query(Newsletter).filter(Newsletter.email_id == email_id).all()
    return {
        "amo": amo,
        "email": email,
        "fxa": fxa,
        "newsletters": newsletters,
        "vpn_waitlist": vpn_waitlist,
    }


def create_amo(db: Session, email_id: UUID, amo: AddOnsSchema):
    db_amo = AmoAccount(email_id=email_id, **amo.dict())
    db.add(db_amo)
    db.commit()
    db.refresh(db_amo)
    return db_amo


def create_email(db: Session, email: EmailSchema):
    db_email = Email(**email.dict())
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email


def create_fxa(db: Session, email_id: UUID, fxa: FirefoxAccountsSchema):
    db_fxa = FirefoxAccount(email_id=email_id, **fxa.dict())
    db.add(db_fxa)
    db.commit()
    db.refresh(db_fxa)
    return db_fxa


def create_vpn_waitlist(db: Session, email_id: UUID, vpn_waitlist: VpnWaitlistSchema):
    db_vpn_waitlist = VpnWaitlist(email_id=email_id, **vpn_waitlist.dict())
    db.add(db_vpn_waitlist)
    db.commit()
    db.refresh(db_vpn_waitlist)
    return db_vpn_waitlist


def create_newsletter(db: Session, email_id: UUID, newsletter: NewsletterSchema):
    db_newsletter = Newsletter(email_id=email_id, **newsletter.dict())
    db.add(db_newsletter)
    db.commit()
    db.refresh(db_newsletter)
    return db_newsletter
