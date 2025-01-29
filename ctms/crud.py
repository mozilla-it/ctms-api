from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, cast

from pydantic import UUID4
from sqlalchemy import asc, or_, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload, load_only, selectinload
from sqlalchemy.sql import func

from .auth import hash_password
from .models import (
    AmoAccount,
    ApiClient,
    Base,
    Email,
    FirefoxAccount,
    MozillaFoundationContact,
    Newsletter,
    Waitlist,
)
from .schemas import (
    AddOnsInSchema,
    ApiClientSchema,
    ContactInSchema,
    ContactPutSchema,
    ContactSchema,
    EmailInSchema,
    EmailPutSchema,
    FirefoxAccountsInSchema,
    MozillaFoundationInSchema,
    NewsletterInSchema,
    UpdatedAddOnsInSchema,
    UpdatedEmailPutSchema,
    UpdatedFirefoxAccountsInSchema,
    WaitlistInSchema,
)

logger = logging.getLogger(__name__)


def ping(db: Session):
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.exception(exc)
        return False


def count_total_contacts(db: Session) -> int:
    """Return the total number of email records.

    Since the table is huge, we rely on the PostgreSQL internal
    catalog to retrieve an approximate size efficiently.
    This metadata is refreshed on `VACUUM` or `ANALYSIS` which
    is run regularly by default on our database instances.
    """
    result = db.execute(text("SELECT reltuples AS estimate " "FROM pg_class " f"where relname = '{Email.__tablename__}'")).scalar()
    if result is None or result < 0:
        # Fall back to a full count if the estimate is not available.
        result = db.execute(text(f"SELECT COUNT(*) FROM {Email.__tablename__}")).scalar()
    if result is None:
        return -1
    return int(result)


def get_amo_by_email_id(db: Session, email_id: UUID4):
    return db.query(AmoAccount).filter(AmoAccount.email_id == email_id).one_or_none()


def get_fxa_by_email_id(db: Session, email_id: UUID4):
    return db.query(FirefoxAccount).filter(FirefoxAccount.email_id == email_id).one_or_none()


def get_mofo_by_email_id(db: Session, email_id: UUID4):
    return db.query(MozillaFoundationContact).filter(MozillaFoundationContact.email_id == email_id).one_or_none()


def get_newsletters_by_email_id(db: Session, email_id: UUID4):
    return db.query(Newsletter).filter(Newsletter.email_id == email_id).all()


def get_waitlists_by_email_id(db: Session, email_id: UUID4):
    return db.query(Waitlist).filter(Waitlist.email_id == email_id).all()


def _contact_base_query(db):
    """Return a query that will fetch related contact data, ready to filter."""
    return (
        db.query(Email)
        .options(joinedload(Email.amo))
        .options(joinedload(Email.fxa))
        .options(joinedload(Email.mofo))
        .options(selectinload(Email.newsletters))
        .options(selectinload(Email.waitlists))
    )


def get_all_contacts_from_ids(db, email_ids):
    """Fetch all contacts that have the specified IDs."""
    bulk_contacts = _contact_base_query(db)
    return bulk_contacts.filter(Email.email_id.in_(email_ids)).all()


def get_bulk_query(start_time, end_time, after_email_uuid, mofo_relevant):
    filters = [
        Email.update_timestamp >= start_time,
        Email.update_timestamp < end_time,
        Email.email_id != after_email_uuid,
    ]
    if mofo_relevant is False:
        filters.append(
            or_(
                Email.mofo == None,
                Email.mofo.has(mofo_relevant=mofo_relevant),
            )
        )
    if mofo_relevant is True:
        filters.append(Email.mofo.has(mofo_relevant=mofo_relevant))
    return filters


def get_bulk_contacts(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    limit: int,
    mofo_relevant: Optional[bool] = None,
    after_email_id: Optional[str] = None,
):
    """Get all the data for a bulk batched set of contacts."""
    after_email_uuid = None
    if after_email_id is not None:
        after_email_uuid = uuid.UUID(after_email_id)
    filter_list = get_bulk_query(
        start_time=start_time,
        end_time=end_time,
        after_email_uuid=after_email_uuid,
        mofo_relevant=mofo_relevant,
    )
    bulk_contacts = _contact_base_query(db)
    for query_filter in filter_list:
        bulk_contacts = bulk_contacts.filter(query_filter)

    bulk_contacts = bulk_contacts.order_by(asc(Email.update_timestamp), asc(Email.email_id)).limit(limit).all()

    return [ContactSchema.from_email(email) for email in bulk_contacts]


def get_email(db: Session, email_id: UUID4) -> Optional[Email]:
    """Get an Email and all related data."""
    return cast(
        Optional[Email],
        _contact_base_query(db).filter(Email.email_id == email_id).one_or_none(),
    )


def get_contact_by_email_id(db: Session, email_id: UUID4) -> Optional[ContactSchema]:
    """Return a Contact object for a given email id"""
    email = get_email(db, email_id)
    if email is None:
        return None
    return ContactSchema.from_email(email)


def get_contacts_by_any_id(
    db: Session,
    email_id: Optional[UUID4] = None,
    primary_email: Optional[str] = None,
    basket_token: Optional[UUID4] = None,
    sfdc_id: Optional[str] = None,
    mofo_contact_id: Optional[str] = None,
    mofo_email_id: Optional[str] = None,
    amo_user_id: Optional[str] = None,
    fxa_id: Optional[str] = None,
    fxa_primary_email: Optional[str] = None,
) -> List[ContactSchema]:
    """
    Get all the data for multiple contacts by ID as a list of Contacts.

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
        statement = statement.filter_by(primary_email_insensitive_comparator=primary_email)
    if basket_token is not None:
        statement = statement.filter(Email.basket_token == str(basket_token))
    if sfdc_id is not None:
        statement = statement.filter(Email.sfdc_id == sfdc_id)
    if mofo_contact_id is not None:
        statement = statement.join(Email.mofo).filter(MozillaFoundationContact.mofo_contact_id == mofo_contact_id)
    if mofo_email_id is not None:
        statement = statement.join(Email.mofo).filter(MozillaFoundationContact.mofo_email_id == mofo_email_id)
    if amo_user_id is not None:
        statement = statement.join(Email.amo).filter(AmoAccount.user_id == amo_user_id)
    if fxa_id is not None:
        statement = statement.join(Email.fxa).filter(FirefoxAccount.fxa_id == fxa_id)
    if fxa_primary_email is not None:
        statement = statement.join(Email.fxa).filter_by(fxa_primary_email_insensitive_comparator=fxa_primary_email)
    emails = cast(List[Email], statement.all())
    return [ContactSchema.from_email(email) for email in emails]


def create_amo(db: Session, email_id: UUID4, amo: AddOnsInSchema) -> Optional[AmoAccount]:
    if amo.is_default():
        return None
    db_amo = AmoAccount(email_id=email_id, **amo.model_dump())
    db.add(db_amo)
    return db_amo


def create_or_update_amo(db: Session, email_id: UUID4, amo: Optional[AddOnsInSchema]):
    if not amo or amo.is_default():
        db.query(AmoAccount).filter(AmoAccount.email_id == email_id).delete()
        return

    # Providing update timestamp
    updated_amo = UpdatedAddOnsInSchema(**amo.model_dump())
    stmt = insert(AmoAccount).values(email_id=email_id, **updated_amo.model_dump())
    stmt = stmt.on_conflict_do_update(index_elements=[AmoAccount.email_id], set_=updated_amo.model_dump())
    db.execute(stmt)


def create_email(db: Session, email: EmailInSchema):
    db_email = Email(**email.model_dump())
    db.add(db_email)


def create_or_update_email(db: Session, email: EmailPutSchema):
    # Providing update timestamp
    updated_email = UpdatedEmailPutSchema(**email.model_dump())

    stmt = insert(Email).values(**updated_email.model_dump())
    stmt = stmt.on_conflict_do_update(index_elements=[Email.email_id], set_=updated_email.model_dump())
    db.execute(stmt)


def create_fxa(db: Session, email_id: UUID4, fxa: FirefoxAccountsInSchema) -> Optional[FirefoxAccount]:
    if fxa.is_default():
        return None
    db_fxa = FirefoxAccount(email_id=email_id, **fxa.model_dump())
    db.add(db_fxa)
    return db_fxa


def create_or_update_fxa(db: Session, email_id: UUID4, fxa: Optional[FirefoxAccountsInSchema]):
    if not fxa or fxa.is_default():
        (db.query(FirefoxAccount).filter(FirefoxAccount.email_id == email_id).delete())
        return
    # Providing update timestamp
    updated_fxa = UpdatedFirefoxAccountsInSchema(**fxa.model_dump())

    stmt = insert(FirefoxAccount).values(email_id=email_id, **updated_fxa.model_dump())
    stmt = stmt.on_conflict_do_update(index_elements=[FirefoxAccount.email_id], set_=updated_fxa.model_dump())
    db.execute(stmt)


def create_mofo(db: Session, email_id: UUID4, mofo: MozillaFoundationInSchema) -> Optional[MozillaFoundationContact]:
    if mofo.is_default():
        return None
    db_mofo = MozillaFoundationContact(email_id=email_id, **mofo.model_dump())
    db.add(db_mofo)
    return db_mofo


def create_or_update_mofo(db: Session, email_id: UUID4, mofo: Optional[MozillaFoundationInSchema]):
    if not mofo or mofo.is_default():
        (db.query(MozillaFoundationContact).filter(MozillaFoundationContact.email_id == email_id).delete())
        return
    stmt = insert(MozillaFoundationContact).values(email_id=email_id, **mofo.model_dump())
    stmt = stmt.on_conflict_do_update(index_elements=[MozillaFoundationContact.email_id], set_=mofo.model_dump())
    db.execute(stmt)


def create_newsletter(db: Session, email_id: UUID4, newsletter: NewsletterInSchema) -> Optional[Newsletter]:
    if newsletter.is_default():
        return None
    db_newsletter = Newsletter(email_id=email_id, **newsletter.model_dump())
    db.add(db_newsletter)
    return db_newsletter


def create_or_update_newsletters(db: Session, email_id: UUID4, newsletters: List[NewsletterInSchema]):
    # Start by deleting the existing newsletters that are not specified as input.
    # We delete instead of set subscribed=False, because we want an idempotent
    # round-trip of PUT/GET at the API level.
    names = [newsletter.name for newsletter in newsletters if not newsletter.is_default()]
    db.query(Newsletter).filter(Newsletter.email_id == email_id, Newsletter.name.notin_(names)).delete(
        # Do not bother synchronizing objects in the session.
        # We won't have stale objects because the next upsert query will update
        # the other remaining objects (equivalent to `Waitlist.name.in_(names)`).
        synchronize_session=False
    )

    if newsletters:
        stmt = insert(Newsletter).values([{"email_id": email_id, **n.model_dump()} for n in newsletters])
        stmt = stmt.on_conflict_do_update(
            constraint="uix_email_name",
            set_={
                **dict(stmt.excluded),
                "update_timestamp": text("statement_timestamp()"),
            },
        )

        db.execute(stmt)


def create_waitlist(db: Session, email_id: UUID4, waitlist: WaitlistInSchema) -> Optional[Waitlist]:
    if waitlist.is_default():
        return None
    db_waitlist = Waitlist(email_id=email_id, **waitlist.model_dump())
    db.add(db_waitlist)
    return db_waitlist


def create_or_update_waitlists(db: Session, email_id: UUID4, waitlists: List[WaitlistInSchema]):
    # Start by deleting the existing waitlists that are not specified as input.
    # We delete instead of set subscribed=False, because we want an idempotent
    # round-trip of PUT/GET at the API level.
    # Note: the contact is marked as pending synchronization at the API routers level.
    names = [waitlist.name for waitlist in waitlists if not waitlist.is_default()]
    db.query(Waitlist).filter(Waitlist.email_id == email_id, Waitlist.name.notin_(names)).delete(
        # Do not bother synchronizing objects in the session.
        # We won't have stale objects because the next upsert query will update
        # the other remaining objects (equivalent to `Waitlist.name.in_(names)`).
        synchronize_session=False
    )
    waitlists_to_upsert = [WaitlistInSchema(**waitlist.model_dump()) for waitlist in waitlists]
    if waitlists_to_upsert:
        stmt = insert(Waitlist).values([{"email_id": email_id, **wl.model_dump()} for wl in waitlists])
        stmt = stmt.on_conflict_do_update(
            constraint="uix_wl_email_name",
            set_={
                **dict(stmt.excluded),
                "update_timestamp": text("statement_timestamp()"),
            },
        )

        db.execute(stmt)


def create_contact(
    db: Session,
    email_id: UUID4,
    contact: ContactInSchema,
    metrics: Optional[Dict],
):
    create_email(db, contact.email)
    if contact.amo:
        create_amo(db, email_id, contact.amo)
    if contact.fxa:
        create_fxa(db, email_id, contact.fxa)
    if contact.mofo:
        create_mofo(db, email_id, contact.mofo)

    for newsletter in contact.newsletters:
        create_newsletter(db, email_id, newsletter)

    for waitlist in contact.waitlists:
        create_waitlist(db, email_id, waitlist)


def create_or_update_contact(db: Session, email_id: UUID4, contact: ContactPutSchema, metrics: Optional[Dict]):
    create_or_update_email(db, contact.email)
    create_or_update_amo(db, email_id, contact.amo)
    create_or_update_fxa(db, email_id, contact.fxa)
    create_or_update_mofo(db, email_id, contact.mofo)

    create_or_update_newsletters(db, email_id, contact.newsletters)
    create_or_update_waitlists(db, email_id, contact.waitlists)


def delete_contact(db: Session, email_id: UUID4):
    db.query(AmoAccount).filter(AmoAccount.email_id == email_id).delete()
    db.query(MozillaFoundationContact).filter(MozillaFoundationContact.email_id == email_id).delete()
    db.query(Newsletter).filter(Newsletter.email_id == email_id).delete()
    db.query(Waitlist).filter(Waitlist.email_id == email_id).delete()
    db.query(FirefoxAccount).filter(FirefoxAccount.email_id == email_id).delete()
    db.query(Email).filter(Email.email_id == email_id).delete()

    db.commit()


def _update_orm(orm: Base, update_dict: dict):
    """Update a SQLAlchemy model from an update dictionary."""
    for key, value in update_dict.items():
        setattr(orm, key, value)


def update_contact(  # noqa: PLR0912
    db: Session, email: Email, update_data: dict, metrics: Optional[Dict]
) -> None:
    """Update an existing contact using a sparse update dictionary"""
    email_id = email.email_id

    if "email" in update_data:
        _update_orm(email, update_data["email"])

    simple_groups: Dict[str, Tuple[Callable[[Session, UUID4, Any], Optional[Base]], Type[Any]]] = {
        "amo": (create_amo, AddOnsInSchema),
        "fxa": (create_fxa, FirefoxAccountsInSchema),
        "mofo": (create_mofo, MozillaFoundationInSchema),
    }
    for group_name, (creator, schema) in simple_groups.items():
        if group_name in update_data:
            existing = getattr(email, group_name)
            if update_data[group_name] == "DELETE":
                if existing:
                    db.delete(existing)
                    setattr(email, group_name, None)
            elif existing is None:
                new = creator(db, email_id, schema(**update_data[group_name]))
                setattr(email, group_name, new)
            else:
                _update_orm(existing, update_data[group_name])
                if schema.model_validate(existing).is_default():
                    db.delete(existing)
                    setattr(email, group_name, None)

    if "newsletters" in update_data:
        if update_data["newsletters"] == "UNSUBSCRIBE":
            for newsletter in getattr(email, "newsletters", []):
                _update_orm(newsletter, {"subscribed": False})
        else:
            existing = {}
            for newsletter in getattr(email, "newsletters", []):
                existing[newsletter.name] = newsletter
            for nl_update in update_data["newsletters"]:
                if nl_update["name"] in existing:
                    _update_orm(existing[nl_update["name"]], nl_update)
                elif nl_update.get("subscribed", True):
                    new = create_newsletter(db, email_id, NewsletterInSchema(**nl_update))
                    email.newsletters.append(new)

    existing = {}
    for waitlist in email.waitlists:
        existing[waitlist.name] = waitlist

    if "waitlists" in update_data:
        if update_data["waitlists"] == "UNSUBSCRIBE":
            for waitlist_orm in existing.values():
                _update_orm(waitlist_orm, {"subscribed": False})
        else:
            for wl_update in update_data["waitlists"]:
                if wl_update["name"] in existing:
                    waitlist_orm = existing[wl_update["name"]]
                    # Update the Waitlist ORM object
                    _update_orm(waitlist_orm, wl_update)
                elif wl_update.get("subscribed", True):
                    new = create_waitlist(db, email_id, WaitlistInSchema(**wl_update))
                    email.waitlists.append(new)

    # On any PATCH event, the central/email table's time is updated as well.
    _update_orm(email, {"update_timestamp": datetime.now(timezone.utc)})


def create_api_client(db: Session, api_client: ApiClientSchema, secret):
    hashed_secret = hash_password(secret)
    db_api_client = ApiClient(hashed_secret=hashed_secret, **api_client.model_dump())
    db.add(db_api_client)


def get_api_client_by_id(db: Session, client_id: str):
    return db.query(ApiClient).filter(ApiClient.client_id == client_id).one_or_none()


def get_active_api_client_ids(db: Session) -> List[str]:
    rows = db.query(ApiClient).filter(ApiClient.enabled.is_(True)).options(load_only(ApiClient.client_id)).order_by(ApiClient.client_id).all()
    return [row.client_id for row in rows]


def update_api_client_last_access(db: Session, api_client: ApiClient):
    api_client.last_access = func.now()
    db.add(api_client)


def get_contacts_from_newsletter(dbsession, newsletter_name):
    entries = (
        dbsession.query(Newsletter)
        .options(joinedload(Newsletter.email))
        .filter(Newsletter.name == newsletter_name, Newsletter.subscribed.is_(True))
        .all()
    )
    return entries


def get_contacts_from_waitlist(dbsession, waitlist_name):
    entries = dbsession.query(Waitlist).options(joinedload(Waitlist.email)).filter(Waitlist.name == waitlist_name).all()
    return entries
