from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, cast

from pydantic import UUID4
from sqlalchemy import asc, or_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload, load_only, selectinload

from .auth import hash_password
from .backport_legacy_waitlists import format_legacy_vpn_relay_waitlist_input
from .database import Base
from .models import (
    AcousticField,
    AcousticNewsletterMapping,
    AmoAccount,
    ApiClient,
    Email,
    FirefoxAccount,
    MozillaFoundationContact,
    Newsletter,
    PendingAcousticRecord,
    StripeBase,
    StripeCustomer,
    StripeInvoice,
    StripeInvoiceLineItem,
    StripePrice,
    StripeSubscription,
    StripeSubscriptionItem,
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
    ProductBaseSchema,
    StripeCustomerCreateSchema,
    StripeInvoiceCreateSchema,
    StripeInvoiceLineItemCreateSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
    UpdatedAddOnsInSchema,
    UpdatedEmailPutSchema,
    UpdatedFirefoxAccountsInSchema,
    UpdatedNewsletterInSchema,
    UpdatedWaitlistInSchema,
    WaitlistInSchema,
)
from .schemas.base import BaseModel


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
        .options(
            joinedload(Email.stripe_customer)
            .subqueryload(StripeCustomer.subscriptions)
            .subqueryload(StripeSubscription.subscription_items)
            .subqueryload(StripeSubscriptionItem.price)
        )
    )


def get_bulk_query(start_time, end_time, after_email_uuid, mofo_relevant):
    filters = [
        Email.update_timestamp >= start_time,
        Email.update_timestamp < end_time,
        Email.email_id != after_email_uuid,
    ]
    if mofo_relevant is False:
        filters.append(
            or_(
                Email.mofo == None,  # pylint: disable=C0121
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

    bulk_contacts = (
        bulk_contacts.order_by(asc(Email.update_timestamp), asc(Email.email_id))
        .limit(limit)
        .all()
    )

    return [
        ContactSchema.parse_obj(
            {
                "amo": email.amo,
                "email": email,
                "fxa": email.fxa,
                "mofo": email.mofo,
                "newsletters": email.newsletters,
                "waitlists": email.waitlists,
            }
        )
        for email in bulk_contacts
    ]


def get_email(db: Session, email_id: UUID4) -> Optional[Email]:
    """Get an Email and all related data."""
    return cast(
        Optional[Email],
        _contact_base_query(db).filter(Email.email_id == email_id).one_or_none(),
    )


def get_contact_by_email_id(db: Session, email_id: UUID4) -> Optional[Dict]:
    """Get all the data for a contact, as a dict."""
    email = get_email(db, email_id)
    if email is None:
        return None
    products = []
    products.extend(get_stripe_products(email))
    return {
        "amo": email.amo,
        "email": email,
        "fxa": email.fxa,
        "mofo": email.mofo,
        "newsletters": email.newsletters,
        "products": products,
        "waitlists": email.waitlists,
    }


def get_emails_by_any_id(
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
        statement = statement.filter_by(
            primary_email_insensitive_comparator=primary_email
        )
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
        statement = statement.join(Email.fxa).filter_by(
            fxa_primary_email_insensitive_comparator=fxa_primary_email
        )
    return cast(List[Email], statement.all())


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
                "waitlists": email.waitlists,
            }
        )
    return data


def _acoustic_sync_retry_query(db: Session):
    return (
        db.query(PendingAcousticRecord)
        .filter(
            PendingAcousticRecord.retry > 0,
        )
        .order_by(
            asc(PendingAcousticRecord.retry),
            asc(PendingAcousticRecord.update_timestamp),
        )
    )


def get_all_acoustic_retries_count(db: Session) -> int:
    """
    Get count of the pending records with >0 retries."""
    query = _acoustic_sync_retry_query(db=db)
    pending_retry_count: int = query.count()
    return pending_retry_count


def _acoustic_sync_base_query(db: Session, end_time: datetime, retry_limit: int = 5):
    return (
        db.query(PendingAcousticRecord)
        .filter(
            PendingAcousticRecord.update_timestamp < end_time,
            PendingAcousticRecord.retry < retry_limit,
        )
        .order_by(
            asc(PendingAcousticRecord.retry),
            asc(PendingAcousticRecord.update_timestamp),
        )
    )


def get_all_acoustic_records_before(
    db: Session, end_time: datetime, retry_limit: int = 5, batch_limit=None
) -> List[PendingAcousticRecord]:
    """
    Get all the pending records before a given date. Allows retry limit to be provided at query time.
    """
    query = _acoustic_sync_base_query(db=db, end_time=end_time, retry_limit=retry_limit)
    if batch_limit:
        query = query.limit(batch_limit)
    pending_records: List[PendingAcousticRecord] = query.all()
    return pending_records


def get_all_acoustic_records_count(
    db: Session, end_time: datetime, retry_limit: int = 5
) -> int:
    """
    Get all the pending records before a given date. Allows retry limit to be provided at query time.
    """
    query = _acoustic_sync_base_query(db=db, end_time=end_time, retry_limit=retry_limit)
    pending_records_count: int = query.count()
    return pending_records_count


def get_acoustic_record_as_contact(
    db: Session,
    record: PendingAcousticRecord,
) -> ContactSchema:
    contact = get_contact_by_email_id(db, record.email_id)
    contact_schema: ContactSchema = ContactSchema.parse_obj(contact)
    return contact_schema


def bulk_schedule_acoustic_records(db: Session, primary_emails: list[str]):
    """Mark a list of primary email as pending synchronization."""
    statement = _contact_base_query(db).filter(Email.primary_email.in_(primary_emails))
    db.bulk_save_objects(
        PendingAcousticRecord(email_id=email.email_id) for email in statement.all()
    )


def reset_retry_acoustic_records(db: Session):
    pending_records = (
        db.query(PendingAcousticRecord).filter(PendingAcousticRecord.retry > 0).all()
    )
    count = len(pending_records)
    db.execute(
        update(PendingAcousticRecord),
        [{"id": record.id, "retry": 0} for record in (pending_records)],
    )
    return count


def schedule_acoustic_record(
    db: Session,
    email_id: UUID4,
    metrics: Optional[Dict] = None,
) -> None:
    db_pending_record = PendingAcousticRecord(email_id=email_id)
    db.add(db_pending_record)
    if metrics:
        metrics["pending_acoustic_sync"].inc()


def retry_acoustic_record(db: Session, pending_record: PendingAcousticRecord) -> None:
    if pending_record.retry is None:
        pending_record.retry = 0
    pending_record.retry += 1
    pending_record.update_timestamp = datetime.now(timezone.utc)


def delete_acoustic_record(db: Session, pending_record: PendingAcousticRecord) -> None:
    db.delete(pending_record)


def create_amo(
    db: Session, email_id: UUID4, amo: AddOnsInSchema
) -> Optional[AmoAccount]:
    if amo.is_default():
        return None
    db_amo = AmoAccount(email_id=email_id, **amo.dict())
    db.add(db_amo)
    return db_amo


def create_or_update_amo(db: Session, email_id: UUID4, amo: Optional[AddOnsInSchema]):
    if not amo or amo.is_default():
        db.query(AmoAccount).filter(AmoAccount.email_id == email_id).delete()
        return

    # Providing update timestamp
    updated_amo = UpdatedAddOnsInSchema(**amo.dict())
    stmt = insert(AmoAccount).values(email_id=email_id, **updated_amo.dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[AmoAccount.email_id], set_=updated_amo.dict()
    )
    db.execute(stmt)


def create_email(db: Session, email: EmailInSchema):
    db_email = Email(**email.dict())
    db.add(db_email)


def create_or_update_email(db: Session, email: EmailPutSchema):
    # Providing update timestamp
    updated_email = UpdatedEmailPutSchema(**email.dict())

    stmt = insert(Email).values(**updated_email.dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[Email.email_id], set_=updated_email.dict()
    )
    db.execute(stmt)


def create_fxa(
    db: Session, email_id: UUID4, fxa: FirefoxAccountsInSchema
) -> Optional[FirefoxAccount]:
    if fxa.is_default():
        return None
    db_fxa = FirefoxAccount(email_id=email_id, **fxa.dict())
    db.add(db_fxa)
    return db_fxa


def create_or_update_fxa(
    db: Session, email_id: UUID4, fxa: Optional[FirefoxAccountsInSchema]
):
    if not fxa or fxa.is_default():
        (db.query(FirefoxAccount).filter(FirefoxAccount.email_id == email_id).delete())
        return
    # Providing update timestamp
    updated_fxa = UpdatedFirefoxAccountsInSchema(**fxa.dict())

    stmt = insert(FirefoxAccount).values(email_id=email_id, **updated_fxa.dict())
    stmt = stmt.on_conflict_do_update(
        index_elements=[FirefoxAccount.email_id], set_=updated_fxa.dict()
    )
    db.execute(stmt)


def create_mofo(
    db: Session, email_id: UUID4, mofo: MozillaFoundationInSchema
) -> Optional[MozillaFoundationContact]:
    if mofo.is_default():
        return None
    db_mofo = MozillaFoundationContact(email_id=email_id, **mofo.dict())
    db.add(db_mofo)
    return db_mofo


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


def create_newsletter(
    db: Session, email_id: UUID4, newsletter: NewsletterInSchema
) -> Optional[Newsletter]:
    if newsletter.is_default():
        return None
    db_newsletter = Newsletter(email_id=email_id, **newsletter.dict())
    db.add(db_newsletter)
    return db_newsletter


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
        newsletters = [UpdatedNewsletterInSchema(**news.dict()) for news in newsletters]
        stmt = insert(Newsletter).values(
            [{"email_id": email_id, **n.dict()} for n in newsletters]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uix_email_name", set_=dict(stmt.excluded)
        )

        db.execute(stmt)


def create_waitlist(
    db: Session, email_id: UUID4, waitlist: WaitlistInSchema
) -> Optional[Waitlist]:
    if waitlist.is_default():
        return None
    if not isinstance(waitlist, WaitlistInSchema):
        # Sample data are used as both input (`WaitlistInSchema`) and internal (`WaitlistSchema`)
        # representations.
        waitlist = WaitlistInSchema(**waitlist.dict())
    db_waitlist = Waitlist(email_id=email_id, **waitlist.orm_dict())
    db.add(db_waitlist)
    return db_waitlist


def create_or_update_waitlists(
    db: Session, email_id: UUID4, waitlists: List[WaitlistInSchema]
):
    # Remove waitlists that are marked as subscribed.
    names_to_delete = [
        waitlist.name for waitlist in waitlists if not waitlist.subscribed
    ]
    if names_to_delete:
        db.query(Waitlist).filter(
            Waitlist.email_id == email_id, Waitlist.name.in_(names_to_delete)
        ).delete(
            synchronize_session=False
        )  # This doesn't need to be synchronized because the next query only alters the other remaining rows. They can happen in whatever order. If you plan to change what the rest of this function does, consider changing this as well!

    waitlists_to_upsert = [
        UpdatedWaitlistInSchema(**waitlist.dict())
        for waitlist in waitlists
        if waitlist.subscribed
    ]
    if waitlists_to_upsert:
        stmt = insert(Waitlist).values(
            [{"email_id": email_id, **wl.orm_dict()} for wl in waitlists_to_upsert]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uix_wl_email_name", set_=dict(stmt.excluded)
        )

        db.execute(stmt)


def create_contact(
    db: Session, email_id: UUID4, contact: ContactInSchema, metrics: Optional[Dict]
):
    create_email(db, contact.email)
    if contact.amo:
        create_amo(db, email_id, contact.amo)
    if contact.fxa:
        create_fxa(db, email_id, contact.fxa)
    if contact.mofo:
        create_mofo(db, email_id, contact.mofo)

    contact = format_legacy_vpn_relay_waitlist_input(
        db, email_id, contact, ContactInSchema, metrics
    )

    for newsletter in contact.newsletters:
        create_newsletter(db, email_id, newsletter)

    for waitlist in contact.waitlists:
        create_waitlist(db, email_id, waitlist)


def create_or_update_contact(
    db: Session, email_id: UUID4, contact: ContactPutSchema, metrics: Optional[Dict]
):
    create_or_update_email(db, contact.email)
    create_or_update_amo(db, email_id, contact.amo)
    create_or_update_fxa(db, email_id, contact.fxa)
    create_or_update_mofo(db, email_id, contact.mofo)

    contact = format_legacy_vpn_relay_waitlist_input(
        db, email_id, contact, ContactPutSchema, metrics
    )

    create_or_update_newsletters(db, email_id, contact.newsletters)
    create_or_update_waitlists(db, email_id, contact.waitlists)


def delete_contact(db: Session, email_id: UUID4):
    db.query(PendingAcousticRecord).filter(
        PendingAcousticRecord.email_id == email_id
    ).delete()
    db.query(AmoAccount).filter(AmoAccount.email_id == email_id).delete()
    db.query(MozillaFoundationContact).filter(
        MozillaFoundationContact.email_id == email_id
    ).delete()
    db.query(Newsletter).filter(Newsletter.email_id == email_id).delete()
    db.query(Waitlist).filter(Waitlist.email_id == email_id).delete()
    db.query(FirefoxAccount).filter(FirefoxAccount.email_id == email_id).delete()
    db.query(Email).filter(Email.email_id == email_id).delete()

    db.commit()


def _update_orm(orm: Base, update_dict: dict):
    """Update a SQLAlchemy model from an update dictionary."""
    for key, value in update_dict.items():
        setattr(orm, key, value)


def update_contact(
    db: Session, email: Email, update_data: dict, metrics: Optional[Dict]
) -> None:
    """Update an existing contact using a sparse update dictionary"""
    email_id = email.email_id

    if "email" in update_data:
        _update_orm(email, update_data["email"])

    simple_groups: Dict[
        str, Tuple[Callable[[Session, UUID4, Any], Optional[Base]], Type[Any]]
    ] = {
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
            else:
                if existing is None:
                    new = creator(db, email_id, schema(**update_data[group_name]))
                    setattr(email, group_name, new)
                else:
                    _update_orm(existing, update_data[group_name])
                    if schema.from_orm(existing).is_default():
                        db.delete(existing)
                        setattr(email, group_name, None)

    update_data = format_legacy_vpn_relay_waitlist_input(
        db, email_id, update_data, dict, metrics
    )

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
                    new = create_newsletter(
                        db, email_id, NewsletterInSchema(**nl_update)
                    )
                    email.newsletters.append(new)

    existing = {}
    for waitlist in email.waitlists:
        existing[waitlist.name] = waitlist

    if "waitlists" in update_data:
        if update_data["waitlists"] == "UNSUBSCRIBE":
            for waitlist_orm in existing.values():
                db.delete(waitlist_orm)
                email.waitlists.remove(waitlist_orm)
        else:
            for wl_update in update_data["waitlists"]:
                if wl_update["name"] in existing:
                    waitlist_orm = existing[wl_update["name"]]
                    # Delete waitlists when `subscribed` is False
                    if not wl_update.get("subscribed", True):
                        db.delete(waitlist_orm)
                        email.waitlists.remove(waitlist_orm)
                    else:
                        # Update the Waitlist ORM object
                        _update_orm(waitlist_orm, wl_update)
                elif wl_update.get("subscribed", True):
                    new = create_waitlist(db, email_id, WaitlistInSchema(**wl_update))
                    email.waitlists.append(new)

    # On any PATCH event, the central/email table's time is updated as well.
    _update_orm(email, {"update_timestamp": datetime.now(timezone.utc)})


def create_api_client(db: Session, api_client: ApiClientSchema, secret):
    hashed_secret = hash_password(secret)
    db_api_client = ApiClient(hashed_secret=hashed_secret, **api_client.dict())
    db.add(db_api_client)


def get_api_client_by_id(db: Session, client_id: str):
    return db.query(ApiClient).filter(ApiClient.client_id == client_id).one_or_none()


def get_active_api_client_ids(db: Session) -> List[str]:
    rows = (
        db.query(ApiClient)
        .filter(ApiClient.enabled.is_(True))
        .options(load_only("client_id"))
        .order_by("client_id")
        .all()
    )
    return [row.client_id for row in rows]


StripeModel = TypeVar("StripeModel", bound=StripeBase)
StripeCreateSchema = TypeVar("StripeCreateSchema", bound=BaseModel)


def _create_stripe(
    model: Type[StripeModel],
    schema: Type[StripeCreateSchema],
    db: Session,
    data: StripeCreateSchema,
) -> StripeModel:
    """Create a Stripe Model."""
    db_obj = model(**data.dict())
    db.add(db_obj)
    return db_obj


create_stripe_customer = partial(
    _create_stripe, StripeCustomer, StripeCustomerCreateSchema
)
create_stripe_invoice = partial(
    _create_stripe, StripeInvoice, StripeInvoiceCreateSchema
)
create_stripe_invoice_line_item = partial(
    _create_stripe, StripeInvoiceLineItem, StripeInvoiceLineItemCreateSchema
)
create_stripe_price = partial(_create_stripe, StripePrice, StripePriceCreateSchema)
create_stripe_subscription = partial(
    _create_stripe, StripeSubscription, StripeSubscriptionCreateSchema
)
create_stripe_subscription_item = partial(
    _create_stripe, StripeSubscriptionItem, StripeSubscriptionItemCreateSchema
)


def _get_stripe(
    model: Type[StripeModel],
    db_session: Session,
    stripe_id: str,
    for_update: bool = False,
) -> Optional[StripeModel]:
    """
    Get a Stripe object by its ID, or None if not found.

    If for_update is True (default False), the row will be locked for update.
    """
    query = db_session.query(model)
    if for_update:
        query = query.with_for_update()
    return cast(
        Optional[StripeModel], query.filter(model.stripe_id == stripe_id).one_or_none()
    )


get_stripe_customer_by_stripe_id = partial(_get_stripe, StripeCustomer)
get_stripe_invoice_by_stripe_id = partial(_get_stripe, StripeInvoice)
get_stripe_invoice_line_item_by_stripe_id = partial(_get_stripe, StripeInvoiceLineItem)
get_stripe_price_by_stripe_id = partial(_get_stripe, StripePrice)
get_stripe_subscription_by_stripe_id = partial(_get_stripe, StripeSubscription)
get_stripe_subscription_item_by_stripe_id = partial(_get_stripe, StripeSubscriptionItem)


def get_stripe_customer_by_fxa_id(
    db_session: Session,
    fxa_id: str,
    for_update: bool = False,
) -> Optional[StripeCustomer]:
    """
    Get a StripeCustomer by FxA ID, or None if not found.

    If for_update is True (default False), the row will be locked for update.
    """
    query = db_session.query(StripeCustomer)
    if for_update:
        query = query.with_for_update()
    obj = query.filter(StripeCustomer.fxa_id == fxa_id).one_or_none()
    return cast(Optional[StripeCustomer], obj)


def get_stripe_products(email: Email) -> List[ProductBaseSchema]:
    """Return a list of Stripe products for the contact, if any."""
    if not email.stripe_customer:
        return []

    base_data: Dict[str, Any] = {
        "payment_service": "stripe",
        # These come from the Payment Method, not imported from Stripe.
        "payment_type": None,
        "card_brand": None,
        "card_last4": None,
        "billing_country": None,
    }
    by_product = defaultdict(list)

    for subscription in email.stripe_customer.subscriptions:
        subscription_data = base_data.copy()
        subscription_data.update(
            {
                "status": subscription.status,
                "created": subscription.stripe_created,
                "start": subscription.start_date,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "canceled_at": subscription.canceled_at,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "ended_at": subscription.ended_at,
            }
        )
        for item in subscription.subscription_items:
            product_data = subscription_data.copy()
            price = item.price
            product_data.update(
                {
                    "product_id": price.stripe_product_id,
                    "product_name": None,  # Products are not imported
                    "price_id": price.stripe_id,
                    "currency": price.currency,
                    "amount": price.unit_amount,
                    "interval_count": price.recurring_interval_count,
                    "interval": price.recurring_interval,
                }
            )
            by_product[price.stripe_product_id].append(product_data)

    products = []
    for subscriptions in by_product.values():
        # Sort to find the latest subscription
        def get_current_period(sub: Dict) -> datetime:
            return cast(datetime, sub["current_period_end"])

        subscriptions.sort(key=get_current_period, reverse=True)
        latest = subscriptions[0]
        data = latest.copy()
        if len(subscriptions) == 1:
            segment_prefix = ""
        else:
            segment_prefix = "re-"
        if latest["status"] == "active":
            if latest["canceled_at"]:
                segment = "cancelling"
                changed = latest["canceled_at"]
            else:
                segment = "active"
                changed = latest["start"]
        elif latest["status"] == "canceled":
            segment = "canceled"
            changed = latest["ended_at"]
        else:
            segment_prefix = ""
            segment = "other"
            changed = latest["created"]

        assert changed
        data.update(
            {
                "sub_count": len(subscriptions),
                "segment": f"{segment_prefix}{segment}",
                "changed": changed,
            }
        )
        products.append(ProductBaseSchema(**data))

    def get_product_id(prod: ProductBaseSchema) -> str:
        return prod.product_id or ""

    products.sort(key=get_product_id)
    return products


def get_all_acoustic_fields(dbsession, tablename=None):
    query = dbsession.query(AcousticField).order_by(
        asc(AcousticField.tablename), asc(AcousticField.field)
    )
    if tablename:
        query = query.filter(AcousticField.tablename == tablename)
    return query.all()


def create_acoustic_field(dbsession, tablename, field):
    row = AcousticField(tablename=tablename, field=field)
    dbsession.merge(row)
    dbsession.commit()
    return row


def delete_acoustic_field(dbsession, tablename, field):
    row = (
        dbsession.query(AcousticField)
        .filter(
            AcousticField.tablename == tablename,
            AcousticField.field == field,
        )
        .one_or_none()
    )
    if row is None:
        return None
    dbsession.delete(row)
    dbsession.commit()
    return row


def get_all_acoustic_newsletters_mapping(dbsession):
    return dbsession.query(AcousticNewsletterMapping).all()


def create_acoustic_newsletters_mapping(dbsession, source, destination):
    row = AcousticNewsletterMapping(source=source, destination=destination)
    # This will fail if the mapping already exists.
    dbsession.add(row)
    dbsession.commit()
    return row


def delete_acoustic_newsletters_mapping(dbsession, source):
    row = (
        dbsession.query(AcousticNewsletterMapping)
        .filter(AcousticNewsletterMapping.source == source)
        .one_or_none()
    )
    if not row:
        return None
    dbsession.delete(row)
    dbsession.commit()
    return row


def get_contacts_from_newsletter(dbsession, newsletter_name):
    entries = (
        dbsession.query(Newsletter)
        .options(joinedload(Newsletter.email))
        .filter(Newsletter.name == newsletter_name, Newsletter.subscribed.is_(True))
        .all()
    )
    return entries


def get_contacts_from_waitlist(dbsession, waitlist_name):
    entries = (
        dbsession.query(Waitlist)
        .options(joinedload(Waitlist.email))
        .filter(Waitlist.name == waitlist_name)
        .all()
    )
    return entries
