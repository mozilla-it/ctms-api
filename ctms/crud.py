from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from datetime import datetime

from pydantic import UUID4, EmailStr
from sqlalchemy import asc
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload, selectinload

from ctms.schemas import ContactSchema

from .auth import hash_password
from .database import Base
from .models import (
    AmoAccount,
    ApiClient,
    Email,
    FirefoxAccount,
    MozillaFoundationContact,
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
    MozillaFoundationInSchema,
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


def get_mofo_by_email_id(db: Session, email_id: UUID4):
    return (
        db.query(MozillaFoundationContact)
        .filter(MozillaFoundationContact.email_id == email_id)
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
        .options(joinedload(Email.mofo))
        .options(joinedload(Email.vpn_waitlist))
        .options(selectinload("newsletters"))
    )

def get_bulk_contacts(
    db: Session,
    start_time: datetime,
    end_time: Union[datetime, str],
    limit: int,
    after_email_id: UUID4 = None,
):
    """Get all the data for a bulk batched set of contacts."""
    print(f"{start_time}\n{end_time}")
    bulk_contacts = (
        _contact_base_query(db)
        .filter(
            start_time <= Email.update_timestamp,
            Email.update_timestamp < end_time,
            Email.email_id != after_email_id,
        )
        .order_by(asc(Email.update_timestamp), asc(Email.email_id))
        .limit(limit)
        .all()
    )

    print(bulk_contacts)
    if bulk_contacts is None:
        return []

    return [
        ContactSchema.parse_obj(
            {
                "amo": email.amo,
                "email": email,
                "fxa": email.fxa,
                "mofo": email.mofo,
                "newsletters": email.newsletters,
                "vpn_waitlist": email.vpn_waitlist,
            }
        )
        for email in bulk_contacts
    ]

def get_email(db: Session, email_id: UUID4) -> Email:
    """Get an Email and all related data."""
    return _contact_base_query(db).filter(Email.email_id == email_id).one_or_none()


def get_contact_by_email_id(db: Session, email_id: UUID4) -> Dict:
    """Get all the data for a contact, as a dict."""
    email = get_email(db, email_id)
    if email is None:
        return None
    return {
        "amo": email.amo,
        "email": email,
        "fxa": email.fxa,
        "mofo": email.mofo,
        "newsletters": email.newsletters,
        "vpn_waitlist": email.vpn_waitlist,
    }


def get_emails_by_any_id(
    db: Session,
    email_id: Optional[UUID4] = None,
    primary_email: Optional[EmailStr] = None,
    basket_token: Optional[UUID4] = None,
    sfdc_id: Optional[str] = None,
    mofo_contact_id: Optional[str] = None,
    mofo_email_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[EmailStr] = None,
) -> List[Email]:
    """
    Get all the data for multiple contacts by IDs as a list of Email instances.

    Newsletters are retrieved in batches of 500 email_ids, so it will be two
    queries for most calls.
    """
    assert any(
        (
            email_id,
            primary_email,
            basket_token,
            sfdc_id,
            mofo_email_id,
            mofo_contact_id,
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
    if mofo_contact_id is not None:
        statement = statement.join(Email.mofo).filter(
            MozillaFoundationContact.mofo_contact_id == mofo_contact_id
        )
    if mofo_email_id is not None:
        statement = statement.join(Email.mofo).filter(
            MozillaFoundationContact.mofo_email_id == mofo_email_id
        )
    if amo_user_id is not None:
        statement = statement.join(Email.amo).filter(AmoAccount.user_id == amo_user_id)
    if fxa_id is not None:
        statement = statement.join(Email.fxa).filter(FirefoxAccount.fxa_id == fxa_id)
    if fxa_primary_email is not None:
        statement = statement.join(Email.fxa).filter(
            FirefoxAccount.primary_email == fxa_primary_email
        )
    return statement.all()


def get_contacts_by_any_id(
    db: Session,
    email_id: Optional[UUID4] = None,
    primary_email: Optional[EmailStr] = None,
    basket_token: Optional[UUID4] = None,
    sfdc_id: Optional[str] = None,
    mofo_contact_id: Optional[str] = None,
    mofo_email_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[EmailStr] = None,
) -> List[Dict]:
    """
    Get all the data for multiple contacts by ID as a list of dicts.

    Newsletters are retrieved in batches of 500 email_ids, so it will be two
    queries for most calls.
    """
    emails = get_emails_by_any_id(
        db,
        email_id,
        primary_email,
        basket_token,
        sfdc_id,
        mofo_contact_id,
        mofo_email_id,
        amo_user_id,
        fxa_id,
        fxa_primary_email,
    )
    data = []
    for email in emails:
        data.append(
            {
                "amo": email.amo,
                "email": email,
                "fxa": email.fxa,
                "mofo": email.mofo,
                "newsletters": email.newsletters,
                "vpn_waitlist": email.vpn_waitlist,
            }
        )
    return data


def create_amo(db: Session, email_id: UUID4, amo: AddOnsInSchema) -> None:
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


def create_fxa(db: Session, email_id: UUID4, fxa: FirefoxAccountsInSchema) -> None:
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


def create_mofo(db: Session, email_id: UUID4, mofo: MozillaFoundationInSchema) -> None:
    if mofo.is_default():
        return
    db_mofo = MozillaFoundationContact(email_id=email_id, **mofo.dict())
    db.add(db_mofo)


def create_or_update_mofo(
    db: Session, email_id: UUID4, mofo: Optional[MozillaFoundationInSchema]
):
    if not mofo or mofo.is_default():
        (
            db.query(MozillaFoundationContact)
            .filter(MozillaFoundationContact.email_id == email_id)
            .delete()
        )
        return
    stmt = insert(MozillaFoundationContact).values(email_id=email_id, **mofo.dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[MozillaFoundationContact.email_id], set_=mofo.dict()
    )
    db.execute(stmt)


def create_vpn_waitlist(
    db: Session, email_id: UUID4, vpn_waitlist: VpnWaitlistInSchema
) -> None:
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
        synchronize_session=False
    )  # This doesn't need to be synchronized because the next query only alters the other remaining rows. They can happen in whatever order. If you plan to change what the rest of this function does, consider changing this as well!

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
    if contact.mofo:
        create_mofo(db, email_id, contact.mofo)
    if contact.vpn_waitlist:
        create_vpn_waitlist(db, email_id, contact.vpn_waitlist)
    for newsletter in contact.newsletters:
        create_newsletter(db, email_id, newsletter)


def create_or_update_contact(db: Session, email_id: UUID4, contact: ContactPutSchema):
    create_or_update_email(db, contact.email)
    create_or_update_amo(db, email_id, contact.amo)
    create_or_update_fxa(db, email_id, contact.fxa)
    create_or_update_mofo(db, email_id, contact.mofo)
    create_or_update_vpn_waitlist(db, email_id, contact.vpn_waitlist)
    create_or_update_newsletters(db, email_id, contact.newsletters)


def update_contact(db: Session, email: Email, update_data: dict) -> None:
    """Update an existing contact using a sparse update dictionary"""
    email_id = email.email_id

    def update_orm(orm: Base, update_dict: dict):
        """Update a SQLAlchemy model from an update dictionary."""
        for key, value in update_dict.items():
            setattr(orm, key, value)

    if "email" in update_data:
        update_orm(email, update_data["email"])

    simple_groups: Dict[
        str, Tuple[Callable[[Session, UUID4, Any], None], Type[Any]]
    ] = {
        "amo": (create_amo, AddOnsInSchema),
        "fxa": (create_fxa, FirefoxAccountsInSchema),
        "mofo": (create_mofo, MozillaFoundationInSchema),
        "vpn_waitlist": (create_vpn_waitlist, VpnWaitlistInSchema),
    }
    for group_name, (creator, schema) in simple_groups.items():
        if group_name in update_data:
            existing = getattr(email, group_name)
            if existing is None:
                creator(db, email_id, schema(**update_data[group_name]))
            else:
                update_orm(existing, update_data[group_name])
                if schema.from_orm(existing).is_default():
                    db.delete(existing)

    if "newsletters" in update_data:
        existing = {}
        for newsletter in getattr(email, "newsletters", []):
            existing[newsletter.name] = newsletter
        for nl_update in update_data["newsletters"]:
            if nl_update["name"] in existing:
                update_orm(existing[nl_update["name"]], nl_update)
            elif nl_update.get("subscribed", True):
                create_newsletter(db, email_id, NewsletterInSchema(**nl_update))


def create_api_client(db: Session, api_client: ApiClientSchema, secret):
    hashed_secret = hash_password(secret)
    db_api_client = ApiClient(hashed_secret=hashed_secret, **api_client.dict())
    db.add(db_api_client)


def get_api_client_by_id(db: Session, client_id: str):
    return db.query(ApiClient).filter(ApiClient.client_id == client_id).one_or_none()
