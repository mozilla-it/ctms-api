from typing import Dict, List, Optional

from pydantic import UUID4, EmailStr
from sqlalchemy.dialects.postgresql import insert
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
    ApiClientSchema,
    ContactInSchema,
    ContactPutSchema,
    EmailInSchema,
    EmailPutSchema,
    FirefoxAccountsInSchema,
    NewsletterInSchema,
    VpnWaitlistInSchema,
)


def get_amo_by_email_id(db: Session, email_id: UUID4):
    return db.query(AmoAccount).filter(AmoAccount.email_id == email_id).one_or_none()


def get_fxa_by_email_id(db: Session, email_id: UUID4):
    return (
        db.query(FirefoxAccount)
        .filter(FirefoxAccount.email_id == email_id)
        .one_or_none()
    )


def get_newsletters_by_email_id(db: Session, email_id: UUID4):
    return db.query(Newsletter).filter(Newsletter.email_id == email_id).all()


def get_vpn_by_email_id(db: Session, email_id: UUID4):
    return db.query(VpnWaitlist).filter(VpnWaitlist.email_id == email_id).one_or_none()


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


def create_or_update_amo(db: Session, email_id: UUID4, amo: Optional[AddOnsInSchema]):
    if not amo or amo.is_default():
        db.query(AmoAccount).filter(AmoAccount.email_id == email_id).delete()
        return
    stmt = insert(AmoAccount).values(email_id=email_id, **amo.dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[AmoAccount.email_id], set_=amo.dict()
    )
    db.execute(stmt)


def create_email(db: Session, email: EmailInSchema):
    db_email = Email(**email.dict())
    db.add(db_email)


def create_or_update_email(db: Session, email: EmailPutSchema):
    stmt = insert(Email).values(**email.dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[Email.email_id], set_=email.dict()
    )
    db.execute(stmt)


def create_fxa(db: Session, email_id: UUID4, fxa: FirefoxAccountsInSchema):
    if fxa.is_default():
        return
    db_fxa = FirefoxAccount(email_id=email_id, **fxa.dict())
    db.add(db_fxa)


def create_or_update_fxa(
    db: Session, email_id: UUID4, fxa: Optional[FirefoxAccountsInSchema]
):
    if not fxa or fxa.is_default():
        (db.query(FirefoxAccount).filter(FirefoxAccount.email_id == email_id).delete())
        return
    stmt = insert(FirefoxAccount).values(email_id=email_id, **fxa.dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[FirefoxAccount.email_id], set_=fxa.dict()
    )
    db.execute(stmt)


def create_vpn_waitlist(
    db: Session, email_id: UUID4, vpn_waitlist: VpnWaitlistInSchema
):
    if vpn_waitlist.is_default():
        return
    db_vpn_waitlist = VpnWaitlist(email_id=email_id, **vpn_waitlist.dict())
    db.add(db_vpn_waitlist)


def create_or_update_vpn_waitlist(
    db: Session, email_id: UUID4, vpn_waitlist: Optional[VpnWaitlistInSchema]
):
    if not vpn_waitlist or vpn_waitlist.is_default():
        db.query(VpnWaitlist).filter(VpnWaitlist.email_id == email_id).delete()
        return
    stmt = insert(VpnWaitlist).values(email_id=email_id, **vpn_waitlist.dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[VpnWaitlist.email_id], set_=vpn_waitlist.dict()
    )
    db.execute(stmt)


def create_newsletter(db: Session, email_id: UUID4, newsletter: NewsletterInSchema):
    if newsletter.is_default():
        return
    db_newsletter = Newsletter(email_id=email_id, **newsletter.dict())
    db.add(db_newsletter)


def create_or_update_newsletters(
    db: Session, email_id: UUID4, newsletters: List[NewsletterInSchema]
):
    names = [
        newsletter.name for newsletter in newsletters if not newsletter.is_default()
    ]
    db.query(Newsletter).filter(
        Newsletter.email_id == email_id, Newsletter.name.notin_(names)
    ).delete(
        synchronize_session="fetch"
    )  # TODO: investigate if this is the right sync_session

    # TODO: figure out on_conflict here

    if newsletters:
        stmt = insert(Newsletter).values(
            [{"email_id": email_id, **n.dict()} for n in newsletters]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uix_email_name", set_=dict(stmt.excluded)
        )

        db.execute(stmt)


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


def create_or_update_contact(db: Session, email_id: UUID4, contact: ContactPutSchema):
    create_or_update_email(db, contact.email)
    create_or_update_amo(db, email_id, contact.amo)
    create_or_update_fxa(db, email_id, contact.fxa)
    create_or_update_vpn_waitlist(db, email_id, contact.vpn_waitlist)
    create_or_update_newsletters(db, email_id, contact.newsletters)


def create_api_client(db: Session, api_client: ApiClientSchema, secret):
    hashed_secret = hash_password(secret)
    db_api_client = ApiClient(hashed_secret=hashed_secret, **api_client.dict())
    db.add(db_api_client)


def get_api_client_by_id(db: Session, client_id: str):
    return db.query(ApiClient).filter(ApiClient.client_id == client_id).one_or_none()
