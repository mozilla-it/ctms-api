from typing import Dict, List, Optional

from pydantic import UUID4, EmailStr
from sqlalchemy.orm import Session, joinedload, selectinload

from .auth import hash_password
from .models import (
    AmoAccount,
    ApiClient,
    Email,
    FirefoxAccount,
    Newsletter,
    VpnWaitlist,
)
from .schemas import (
    AddOnsInSchema,
    AddOnsSchema,
    ApiClientSchema,
    ContactInSchema,
    ContactSchema,
    EmailInSchema,
    EmailSchema,
    FirefoxAccountsInSchema,
    FirefoxAccountsSchema,
    NewsletterInSchema,
    NewsletterSchema,
    VpnWaitlistInSchema,
    VpnWaitlistSchema,
)


def get_email_by_email_id(db: Session, email_id: UUID4):
    return db.query(Email).filter(Email.email_id == email_id).first()


def get_amo_by_email_id(db: Session, email_id: UUID4):
    return db.query(AmoAccount).filter(AmoAccount.email_id == email_id).first()


def get_fxa_by_email_id(db: Session, email_id: UUID4):
    return db.query(FirefoxAccount).filter(FirefoxAccount.email_id == email_id).first()


def get_newsletters_by_email_id(db: Session, email_id: UUID4):
    return db.query(Newsletter).filter(Newsletter.email_id == email_id).first()


def get_vpn_by_email_id(db: Session, email_id: UUID4):
    return db.query(VpnWaitlist).filter(VpnWaitlist.email_id == email_id).first()


def _contact_base_query(db):
    """Return a query that will fetch related contact data, ready to filter."""
    return (
        db.query(Email)
        .options(joinedload(Email.amo))
        .options(joinedload(Email.fxa))
        .options(joinedload(Email.vpn_waitlist))
        .options(selectinload("newsletters"))
    )


def get_contact_by_email_id(db: Session, email_id: UUID4):
    """Get all the data for a contact."""
    email = _contact_base_query(db).filter(Email.email_id == email_id).one_or_none()
    if email is None:
        return None
    return {
        "amo": email.amo,
        "email": email,
        "fxa": email.fxa,
        "newsletters": email.newsletters,
        "vpn_waitlist": email.vpn_waitlist,
    }


def get_contacts_by_any_id(
    db: Session,
    email_id: Optional[UUID4] = None,
    primary_email: Optional[EmailStr] = None,
    basket_token: Optional[UUID4] = None,
    sfdc_id: Optional[str] = None,
    mofo_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[EmailStr] = None,
) -> List[Dict]:
    """
    Get all the data for multiple contacts by IDs.

    Newsletters are retrieved in batches of 500 email_ids, so it will be two
    queries for most calls.
    """
    assert any(
        (
            email_id,
            primary_email,
            basket_token,
            sfdc_id,
            mofo_id,
            amo_user_id,
            fxa_id,
            fxa_primary_email,
        )
    )
    statement = _contact_base_query(db)
    if email_id is not None:
        statement = statement.filter(Email.email_id == email_id)
    if primary_email is not None:
        statement = statement.filter(Email.primary_email == primary_email)
    if basket_token is not None:
        statement = statement.filter(Email.basket_token == str(basket_token))
    if sfdc_id is not None:
        statement = statement.filter(Email.sfdc_id == sfdc_id)
    if mofo_id is not None:
        statement = statement.filter(Email.mofo_id == mofo_id)
    if amo_user_id is not None:
        statement = statement.join(Email.amo).filter(AmoAccount.user_id == amo_user_id)
    if fxa_id is not None:
        statement = statement.join(Email.fxa).filter(FirefoxAccount.fxa_id == fxa_id)
    if fxa_primary_email is not None:
        statement = statement.join(Email.fxa).filter(
            FirefoxAccount.primary_email == fxa_primary_email
        )
    results = statement.all()
    data = []
    for email in results:
        data.append(
            {
                "amo": email.amo,
                "email": email,
                "fxa": email.fxa,
                "newsletters": email.newsletters,
                "vpn_waitlist": email.vpn_waitlist,
            }
        )
    return data


def create_amo(db: Session, email_id: UUID4, amo: AddOnsInSchema):
    if amo.is_default():
        return
    db_amo = AmoAccount(email_id=email_id, **amo.dict())
    db.add(db_amo)


def create_email(db: Session, email: EmailInSchema):
    db_email = Email(**email.dict())
    db.add(db_email)


def create_fxa(db: Session, email_id: UUID4, fxa: FirefoxAccountsInSchema):
    if fxa.is_default():
        return
    db_fxa = FirefoxAccount(email_id=email_id, **fxa.dict())
    db.add(db_fxa)


def create_vpn_waitlist(
    db: Session, email_id: UUID4, vpn_waitlist: VpnWaitlistInSchema
):
    if vpn_waitlist.is_default():
        return
    db_vpn_waitlist = VpnWaitlist(email_id=email_id, **vpn_waitlist.dict())
    db.add(db_vpn_waitlist)


def create_newsletter(db: Session, email_id: UUID4, newsletter: NewsletterInSchema):
    if newsletter.is_default():
        return
    db_newsletter = Newsletter(email_id=email_id, **newsletter.dict())
    db.add(db_newsletter)


def create_contact(db: Session, email_id: UUID4, contact: ContactInSchema):
    create_email(db, contact.email)
    if contact.amo:
        create_amo(db, email_id, contact.amo)
    if contact.fxa:
        create_fxa(db, email_id, contact.fxa)
    if contact.vpn_waitlist:
        create_vpn_waitlist(db, email_id, contact.vpn_waitlist)
    for newsletter in contact.newsletters:
        create_newsletter(db, email_id, newsletter)


def create_api_client(db: Session, api_client: ApiClientSchema, secret):
    hashed_secret = hash_password(secret)
    db_api_client = ApiClient(hashed_secret=hashed_secret, **api_client.dict())
    db.add(db_api_client)


def get_api_client_by_id(db: Session, client_id: str):
    return db.query(ApiClient).filter(ApiClient.client_id == client_id).one_or_none()
