"""Test database operations"""
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import uuid4

import pytest
import sqlalchemy.event

from ctms.crud import (
    create_amo,
    create_email,
    create_fxa,
    create_mofo,
    create_newsletter,
    create_stripe_price,
    create_stripe_subscription,
    create_stripe_subscription_item,
    delete_acoustic_record,
    get_acoustic_record_as_contact,
    get_all_acoustic_records_before,
    get_bulk_contacts,
    get_contact_by_email_id,
    get_contacts_by_any_id,
    get_email,
    get_emails_by_any_id,
    get_stripe_subscription_by_stripe_id,
    retry_acoustic_record,
    schedule_acoustic_record,
)
from ctms.models import Email, PendingAcousticRecord
from ctms.schemas import (
    AddOnsInSchema,
    EmailInSchema,
    FirefoxAccountsInSchema,
    MozillaFoundationInSchema,
    NewsletterInSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)
from tests.unit.sample_data import FAKE_STRIPE_ID, SAMPLE_STRIPE_DATA


class StatementWatcher:
    """
    Capture SQL statements emitted by code.

    Based on https://stackoverflow.com/a/33691585/10612

    Use as a context manager to count the number of execute()'s performed
    against the given session / connection.

    Usage:
        with StatementWatcher(dbsession.connection()) as watcher:
            dbsession.query(Email).all()
        assert watcher.count == 1
    """

    def __init__(self, connection):
        self.connection = connection
        self.statements = []

    def __enter__(self):
        sqlalchemy.event.listen(self.connection, "before_cursor_execute", self.callback)
        return self

    def __exit__(self, *args):
        sqlalchemy.event.remove(self.connection, "before_cursor_execute", self.callback)

    def callback(self, conn, cursor, statement, parameters, context, execute_many):
        self.statements.append((statement, parameters, execute_many))

    @property
    def count(self):
        return len(self.statements)


def test_get_email(dbsession, example_contact):
    """An email is retrived in two queries, and newsletters are sorted by name."""
    email_id = example_contact.email.email_id
    with StatementWatcher(dbsession.connection()) as watcher:
        email = get_email(dbsession, email_id)
    assert watcher.count == 2, watcher.statements
    assert email.email_id == email_id
    with StatementWatcher(dbsession.connection()) as watcher:
        newsletter_names = [newsletter.name for newsletter in email.newsletters]
        assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
        assert sorted(newsletter_names) == newsletter_names
    assert watcher.count == 0, watcher.statements


def test_get_email_with_stripe_customer(dbsession, contact_with_stripe_customer):
    """An email with a Stripe subscription retrived in three queries."""
    email_id = contact_with_stripe_customer.email.email_id
    with StatementWatcher(dbsession.connection()) as watcher:
        email = get_email(dbsession, email_id)
    assert watcher.count == 3, watcher.statements
    assert email.email_id == email_id
    newsletter_names = [newsletter.name for newsletter in email.newsletters]
    assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
    assert sorted(newsletter_names) == newsletter_names

    with StatementWatcher(dbsession.connection()) as watcher:
        assert email.stripe_customer.stripe_id == FAKE_STRIPE_ID["Customer"]
        assert len(email.stripe_customer.subscriptions) == 0
    assert watcher.count == 0, watcher.statements


def test_get_email_with_stripe_subscription(
    dbsession, contact_with_stripe_subscription
):
    """An email with a Stripe subscription retrived in five queries."""
    email_id = contact_with_stripe_subscription.email.email_id
    with StatementWatcher(dbsession.connection()) as watcher:
        email = get_email(dbsession, email_id)
    assert watcher.count == 5, watcher.statements
    assert email.email_id == email_id

    with StatementWatcher(dbsession.connection()) as watcher:
        newsletter_names = [newsletter.name for newsletter in email.newsletters]
        assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
        assert sorted(newsletter_names) == newsletter_names

        assert email.stripe_customer.stripe_id == FAKE_STRIPE_ID["Customer"]
        assert len(email.stripe_customer.subscriptions) == 1
        assert len(email.stripe_customer.subscriptions[0].subscription_items) == 1
        assert (
            email.stripe_customer.subscriptions[0].subscription_items[0].price.stripe_id
            == FAKE_STRIPE_ID["Price"]
        )
    assert watcher.count == 0, watcher.statements


def test_get_email_miss(dbsession):
    """A missed email is one query."""
    with StatementWatcher(dbsession.connection()) as watcher:
        email = get_email(dbsession, str(uuid4()))
    assert watcher.count == 1
    assert email is None


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
        ("primary_email", "mozilla-fan@example.com"),
        ("amo_user_id", "123"),
        ("basket_token", "d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
        ("fxa_id", "611b6788-2bba-42a6-98c9-9ce6eb9cbd34"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
        ("mofo_email_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
    ],
)
def test_get_emails_by_any_id(dbsession, sample_contacts, alt_id_name, alt_id_value):
    """An email is fetched by alternate id in two queries."""
    with StatementWatcher(dbsession.connection()) as watcher:
        emails = get_emails_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert watcher.count == 2
    assert len(emails) == 1
    newsletter_names = [newsletter.name for newsletter in emails[0].newsletters]
    assert sorted(newsletter_names) == newsletter_names


def test_get_emails_by_any_id_missing(dbsession, sample_contacts):
    """One query is needed to find no emails."""
    with StatementWatcher(dbsession.connection()) as watcher:
        emails = get_emails_by_any_id(dbsession, basket_token=str(uuid4()))
    assert watcher.count == 1
    assert len(emails) == 0


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("amo_user_id", "123"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
    ],
)
def test_get_multiple_emails_by_any_id(
    dbsession, sample_contacts, alt_id_name, alt_id_value
):
    """Two emails are retrieved in two queries."""

    dupe_id = str(uuid4())
    create_email(
        dbsession,
        EmailInSchema(
            email_id=dupe_id,
            primary_email="dupe@example.com",
            basket_token=str(uuid4()),
            sfdc_id=alt_id_value
            if alt_id_name == "sfdc_id"
            else "other_sdfc_alt_id_value",
        ),
    )
    if alt_id_name == "amo_user_id":
        create_amo(dbsession, dupe_id, AddOnsInSchema(user_id=alt_id_value))
    if alt_id_name == "fxa_primary_email":
        create_fxa(
            dbsession, dupe_id, FirefoxAccountsInSchema(primary_email=alt_id_value)
        )
    if alt_id_name == "mofo_contact_id":
        create_mofo(
            dbsession,
            dupe_id,
            MozillaFoundationInSchema(
                mofo_email_id=str(uuid4()), mofo_contact_id=alt_id_value
            ),
        )

    create_newsletter(dbsession, dupe_id, NewsletterInSchema(name="zzz_sleepy_news"))
    create_newsletter(dbsession, dupe_id, NewsletterInSchema(name="aaa_game_news"))
    dbsession.flush()

    with StatementWatcher(dbsession.connection()) as watcher:
        emails = get_emails_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert watcher.count == 2
    assert len(emails) == 2
    for email in emails:
        newsletter_names = [newsletter.name for newsletter in email.newsletters]
        assert sorted(newsletter_names) == newsletter_names


def test_get_contact_by_email_id_found(dbsession, example_contact):
    """A contact is retrived in two queries, and newsletters are sorted by name."""
    email_id = example_contact.email.email_id
    with StatementWatcher(dbsession.connection()) as watcher:
        contact = get_contact_by_email_id(dbsession, email_id)
    assert watcher.count == 2
    assert contact["email"].email_id == email_id
    newsletter_names = [nl.name for nl in contact["newsletters"]]
    assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
    assert sorted(newsletter_names) == newsletter_names
    assert contact["products"] == []


def test_get_contact_by_email_id_miss(dbsession):
    """A missed contact is 1 query."""
    with StatementWatcher(dbsession.connection()) as watcher:
        contact = get_contact_by_email_id(dbsession, str(uuid4()))
    assert watcher.count == 1
    assert contact is None


def test_schedule_then_get_acoustic_records_before_time(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    for record in contact_list:
        schedule_acoustic_record(dbsession, record.email.email_id)

    dbsession.flush()
    with StatementWatcher(dbsession.connection()) as watcher:
        record_list = get_all_acoustic_records_before(
            dbsession,
            end_time=end_time,
        )
        dbsession.flush()

    assert watcher.count == 1
    assert len(record_list) == 3
    for record in record_list:
        assert record.email is not None
        assert record.retry is not None and record.retry == 0
        assert record.create_timestamp is not None
        assert record.update_timestamp is not None
        assert record.id is not None


def test_schedule_then_get_acoustic_records_as_contacts(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    for record in contact_list:
        schedule_acoustic_record(dbsession, record.email.email_id)
    dbsession.flush()

    record_list = get_all_acoustic_records_before(
        dbsession,
        end_time=end_time,
    )
    dbsession.flush()
    with StatementWatcher(dbsession.connection()) as watcher:

        contact_record_list = [
            get_acoustic_record_as_contact(dbsession, record) for record in record_list
        ]

    assert watcher.count == 6
    assert len(contact_record_list) == 3
    for record in contact_record_list:
        assert record.email is not None


def test_schedule_then_get_acoustic_records_retry_records(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    for record in contact_list:
        schedule_acoustic_record(dbsession, record.email.email_id)
    dbsession.flush()

    with StatementWatcher(dbsession.connection()) as watcher:
        record_list: List[PendingAcousticRecord] = get_all_acoustic_records_before(
            dbsession,
            end_time=end_time,
        )
        for record in record_list:
            retry_acoustic_record(dbsession, record)

        dbsession.flush()

        record_list: List[PendingAcousticRecord] = get_all_acoustic_records_before(
            dbsession,
            end_time=end_time,
        )
        dbsession.flush()

    assert watcher.count == 3
    assert len(record_list) == 3
    for record in record_list:
        assert isinstance(record.email, Email)
        assert record.retry is not None and record.retry > 0
        assert record.create_timestamp != record.update_timestamp
        assert record.id is not None


def test_schedule_then_get_acoustic_records_minimum_retry(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    for record in contact_list:
        schedule_acoustic_record(dbsession, record.email.email_id)

    dbsession.flush()
    with StatementWatcher(dbsession.connection()) as watcher:

        record_list: List[PendingAcousticRecord] = get_all_acoustic_records_before(
            dbsession,
            end_time=end_time,
        )

        for record in record_list:
            retry_acoustic_record(dbsession, record)

        dbsession.flush()

        record_list: List[PendingAcousticRecord] = get_all_acoustic_records_before(
            dbsession, end_time=end_time, retry_limit=1
        )
        dbsession.flush()

    assert watcher.count == 3
    assert len(record_list) == 0


def test_schedule_then_get_acoustic_records_then_delete(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    for record in contact_list:
        schedule_acoustic_record(dbsession, record.email.email_id)

    dbsession.flush()

    with StatementWatcher(dbsession.connection()) as watcher:

        record_list: List[PendingAcousticRecord] = get_all_acoustic_records_before(
            dbsession,
            end_time=end_time,
        )
        assert len(record_list) > 0

        for record in record_list:
            delete_acoustic_record(dbsession, record)

        dbsession.flush()

        record_list: List[PendingAcousticRecord] = get_all_acoustic_records_before(
            dbsession,
            end_time=end_time,
        )
        dbsession.flush()

    assert watcher.count == 3
    assert len(record_list) == 0


def test_get_acoustic_record_no_stripe_customer(dbsession, example_contact):
    """A contact with no associated Stripe customer has no subscriptions."""
    pending = PendingAcousticRecord(email_id=example_contact.email.email_id)
    contact = get_acoustic_record_as_contact(dbsession, pending)
    assert contact.products == []


def test_get_acoustic_record_no_stripe_subscriptions(
    dbsession, contact_with_stripe_customer
):
    """A contact with no Stripe subscriptions has no subscriptions."""
    email_id = contact_with_stripe_customer.email.email_id
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_acoustic_record_as_contact(dbsession, pending)
    assert contact.products == []


def test_get_acoustic_record_one_stripe_subscription(
    dbsession, contact_with_stripe_subscription
):
    """A contact with one Stripe subscription has one product."""
    email_id = contact_with_stripe_subscription.email.email_id
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_acoustic_record_as_contact(dbsession, pending)
    assert len(contact.products) == 1
    product = contact.products[0]
    assert product.dict() == {
        "payment_service": "stripe",
        "product_id": "prod_cHJvZHVjdA",
        "segment": "active",
        "changed": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "sub_count": 1,
        "product_name": None,
        "price_id": "price_cHJpY2U",
        "payment_type": None,
        "card_brand": None,
        "card_last4": None,
        "currency": "usd",
        "amount": 999,
        "billing_country": None,
        "status": "active",
        "interval_count": 1,
        "interval": "month",
        "created": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "start": datetime(2021, 9, 27, tzinfo=timezone.utc),
        "current_period_start": datetime(2021, 10, 27, tzinfo=timezone.utc),
        "current_period_end": datetime(2021, 11, 27, tzinfo=timezone.utc),
        "canceled_at": None,
        "cancel_at_period_end": False,
        "ended_at": None,
    }


def test_get_acoustic_record_two_stripe_subscriptions(
    dbsession, contact_with_stripe_subscription
):
    """A contact with two Stripe subscriptions to different products has two products."""
    email_id = contact_with_stripe_subscription.email.email_id
    now = datetime.now(tz=timezone.utc)
    new_subscription = SAMPLE_STRIPE_DATA["Subscription"].copy()
    new_sub_item = SAMPLE_STRIPE_DATA["SubscriptionItem"].copy()
    new_price = SAMPLE_STRIPE_DATA["Price"].copy()
    new_subscription["stripe_id"] = "sub_new"
    new_subscription["cancel_at_period_end"] = True
    new_subscription["stripe_created"] = now - timedelta(days=45)
    new_subscription["canceled_at"] = now - timedelta(days=1)
    new_subscription["current_period_start"] = now - timedelta(days=15)
    new_subscription["current_period_end"] = now + timedelta(days=15)
    new_subscription["start_date"] = new_subscription["stripe_created"]

    new_price["stripe_id"] = "price_new"
    new_price["stripe_product_id"] = "prod_mozilla_isp"

    new_sub_item["stripe_id"] = "si_new"
    new_sub_item["stripe_subscription_id"] = new_subscription["stripe_id"]
    new_sub_item["stripe_price_id"] = new_price["stripe_id"]

    create_stripe_subscription(
        dbsession, StripeSubscriptionCreateSchema(**new_subscription)
    )
    create_stripe_price(dbsession, StripePriceCreateSchema(**new_price))
    create_stripe_subscription_item(
        dbsession, StripeSubscriptionItemCreateSchema(**new_sub_item)
    )
    dbsession.commit()

    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_acoustic_record_as_contact(dbsession, pending)
    assert len(contact.products) == 2
    product1 = contact.products[0]
    assert product1.product_id == "prod_cHJvZHVjdA"
    assert product1.sub_count == 1
    assert product1.segment == "active"
    product2 = contact.products[1]
    assert product2.product_id == "prod_mozilla_isp"
    assert product2.sub_count == 1
    assert product2.segment == "cancelling"
    assert product2.changed == now - timedelta(days=1)


def test_get_acoustic_record_serial_stripe_subscriptions(
    dbsession, contact_with_stripe_subscription
):
    """A contact with two Stripe subscriptions to the same product has one product."""
    email_id = contact_with_stripe_subscription.email.email_id
    old_subscription = SAMPLE_STRIPE_DATA["Subscription"].copy()
    old_sub_item = SAMPLE_STRIPE_DATA["SubscriptionItem"].copy()
    old_subscription["stripe_id"] = "sub_old"
    old_subscription["cancel_at_period_end"] = True
    old_subscription["stripe_created"] -= timedelta(days=180)
    old_subscription["start_date"] -= timedelta(days=180)
    old_subscription["current_period_start"] -= timedelta(days=180)
    old_subscription["current_period_end"] -= timedelta(days=180)
    old_subscription["canceled_at"] = old_subscription[
        "current_period_end"
    ] - timedelta(days=10)
    old_subscription["status"] = "canceled"

    old_sub_item["stripe_id"] = "si_old"
    old_sub_item["stripe_subscription_id"] = old_subscription["stripe_id"]

    create_stripe_subscription(
        dbsession, StripeSubscriptionCreateSchema(**old_subscription)
    )
    create_stripe_subscription_item(
        dbsession, StripeSubscriptionItemCreateSchema(**old_sub_item)
    )
    dbsession.commit()

    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_acoustic_record_as_contact(dbsession, pending)
    assert len(contact.products) == 1
    product = contact.products[0]
    assert product.product_id == "prod_cHJvZHVjdA"
    assert product.sub_count == 2
    assert product.segment == "re-active"


def test_get_acoustic_record_stripe_subscription_cancelled(
    dbsession, contact_with_stripe_subscription
):
    """A contact with a canceled Stripe subscription is in the canceled segement."""
    subscription = get_stripe_subscription_by_stripe_id(
        dbsession, FAKE_STRIPE_ID["Subscription"]
    )
    subscription.status = "canceled"
    subscription.ended_at = subscription.current_period_end
    dbsession.commit()
    email_id = contact_with_stripe_subscription.email.email_id
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_acoustic_record_as_contact(dbsession, pending)
    assert len(contact.products) == 1
    product = contact.products[0]
    assert product.segment == "canceled"
    assert product.changed == subscription.ended_at


def test_get_acoustic_record_stripe_subscription_other(
    dbsession, contact_with_stripe_subscription
):
    """A contact with a canceled Stripe subscription is in the canceled segement."""
    subscription = get_stripe_subscription_by_stripe_id(
        dbsession, FAKE_STRIPE_ID["Subscription"]
    )
    subscription.status = "unpaid"
    dbsession.commit()
    email_id = contact_with_stripe_subscription.email.email_id
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_acoustic_record_as_contact(dbsession, pending)
    assert len(contact.products) == 1
    product = contact.products[0]
    assert product.segment == "other"
    assert product.changed == subscription.stripe_created


def test_get_bulk_contacts_mofo_relevant_false(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    sorted_list = sorted(
        contact_list,
        key=lambda contact: (contact.email.update_timestamp, contact.email.email_id),
    )
    mofo_relevant_flag = False

    first_contact = sorted_list[0]
    after_start = first_contact.email.update_timestamp - timedelta(hours=12)
    last_contact = sorted_list[-1]
    last_contact_timestamp = last_contact.email.update_timestamp
    end_time = last_contact_timestamp + timedelta(hours=12)

    with StatementWatcher(dbsession.connection()) as watcher:
        bulk_contact_list = get_bulk_contacts(
            dbsession,
            start_time=after_start,
            end_time=end_time,
            limit=10,
            mofo_relevant=mofo_relevant_flag,
        )
    assert watcher.count == 2
    assert len(bulk_contact_list) == 2


def test_get_bulk_contacts_mofo_relevant_true(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    sorted_list = sorted(
        contact_list,
        key=lambda contact: (contact.email.update_timestamp, contact.email.email_id),
    )
    mofo_relevant_flag = True

    first_contact = sorted_list[0]
    after_start = first_contact.email.update_timestamp - timedelta(hours=12)
    last_contact = sorted_list[-1]
    last_contact_timestamp = last_contact.email.update_timestamp
    end_time = last_contact_timestamp + timedelta(hours=12)

    with StatementWatcher(dbsession.connection()) as watcher:
        bulk_contact_list = get_bulk_contacts(
            dbsession,
            start_time=after_start,
            end_time=end_time,
            limit=10,
            mofo_relevant=mofo_relevant_flag,
        )
    assert watcher.count == 2
    assert len(bulk_contact_list) == 1
    for contact in bulk_contact_list:
        assert contact.mofo.mofo_relevant == mofo_relevant_flag


def test_get_bulk_contacts_some_after_higher_limit(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    sorted_list = sorted(
        contact_list,
        key=lambda contact: (contact.email.update_timestamp, contact.email.email_id),
    )

    first_contact = sorted_list[0]
    after_start = first_contact.email.update_timestamp
    after_id = str(first_contact.email.email_id)
    last_contact = sorted_list[-1]
    last_contact_timestamp = last_contact.email.update_timestamp
    end_time = last_contact_timestamp + timedelta(hours=12)

    with StatementWatcher(dbsession.connection()) as watcher:
        bulk_contact_list = get_bulk_contacts(
            dbsession,
            start_time=after_start,
            end_time=end_time,
            limit=2,
            after_email_id=after_id,
        )
    assert watcher.count == 2
    assert len(bulk_contact_list) == 2
    assert last_contact in bulk_contact_list
    assert sorted_list[-2] in bulk_contact_list


def test_get_bulk_contacts_some_after(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    sorted_list = sorted(
        contact_list,
        key=lambda contact: (contact.email.update_timestamp, contact.email.email_id),
    )

    second_to_last_contact = sorted_list[-2]
    after_start = second_to_last_contact.email.update_timestamp
    after_id = str(second_to_last_contact.email.email_id)
    last_contact = sorted_list[-1]
    last_contact_timestamp = last_contact.email.update_timestamp
    end_time = last_contact_timestamp + timedelta(hours=12)

    with StatementWatcher(dbsession.connection()) as watcher:
        bulk_contact_list = get_bulk_contacts(
            dbsession,
            start_time=after_start,
            end_time=end_time,
            limit=1,
            after_email_id=after_id,
        )
    assert watcher.count == 2
    assert len(bulk_contact_list) == 1
    assert last_contact in bulk_contact_list


def test_get_bulk_contacts_some(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    example_timestamp: datetime = example_contact.email.update_timestamp
    maximal_timestamp: datetime = maximal_contact.email.update_timestamp
    minimal_timestamp: datetime = minimal_contact.email.update_timestamp

    oldest_timestamp = min([example_timestamp, maximal_timestamp, minimal_timestamp])
    timestamp = oldest_timestamp - timedelta(hours=12)

    with StatementWatcher(dbsession.connection()) as watcher:
        bulk_contact_list = get_bulk_contacts(
            dbsession,
            start_time=timestamp,
            end_time=datetime.now(timezone.utc),
            limit=10,
        )
    assert watcher.count == 2
    assert len(bulk_contact_list) == 3
    assert example_contact in bulk_contact_list
    assert maximal_contact in bulk_contact_list
    assert minimal_contact in bulk_contact_list


def test_get_bulk_contacts_one(dbsession, example_contact):
    email_id = example_contact.email.email_id
    timestamp: datetime = example_contact.email.update_timestamp
    start_time = timestamp - timedelta(12)
    end_time = timestamp + timedelta(hours=12)

    with StatementWatcher(dbsession.connection()) as watcher:
        bulk_contact_list = get_bulk_contacts(
            dbsession, start_time=start_time, end_time=end_time, limit=10
        )
    assert watcher.count == 2
    assert len(bulk_contact_list) == 1
    assert bulk_contact_list[0].email.email_id == email_id


def test_get_bulk_contacts_none(dbsession):
    with StatementWatcher(dbsession.connection()) as watcher:
        bulk_contact_list = get_bulk_contacts(
            dbsession,
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
            end_time=datetime.now(timezone.utc) + timedelta(days=1),
            limit=10,
        )
    assert watcher.count == 1
    assert bulk_contact_list == []


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
        ("primary_email", "mozilla-fan@example.com"),
        ("amo_user_id", "123"),
        ("basket_token", "d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
        ("fxa_id", "611b6788-2bba-42a6-98c9-9ce6eb9cbd34"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
        ("mofo_email_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
    ],
)
def test_get_contact_by_any_id(dbsession, sample_contacts, alt_id_name, alt_id_value):
    """A contacts is fetched by alternate id in two queries."""
    with StatementWatcher(dbsession.connection()) as watcher:
        contacts = get_contacts_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert watcher.count == 2
    assert len(contacts) == 1
    newsletter_names = [nl.name for nl in contacts[0]["newsletters"]]
    assert sorted(newsletter_names) == newsletter_names


def test_get_contact_by_any_id_missing(dbsession, sample_contacts):
    """A contacts is fetched by alternate id in two queries."""
    with StatementWatcher(dbsession.connection()) as watcher:
        contact = get_contacts_by_any_id(dbsession, basket_token=str(uuid4()))
    assert watcher.count == 1
    assert len(contact) == 0


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("amo_user_id", "123"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
    ],
)
def test_get_multiple_contacts_by_any_id(
    dbsession, sample_contacts, alt_id_name, alt_id_value
):
    """2 contacts are retrieved in 2 queries."""

    dupe_id = str(uuid4())
    create_email(
        dbsession,
        EmailInSchema(
            email_id=dupe_id,
            primary_email="dupe@example.com",
            basket_token=str(uuid4()),
            sfdc_id=alt_id_value
            if alt_id_name == "sfdc_id"
            else "other_sdfc_alt_id_value",
        ),
    )
    if alt_id_name == "amo_user_id":
        create_amo(dbsession, dupe_id, AddOnsInSchema(user_id=alt_id_value))
    if alt_id_name == "fxa_primary_email":
        create_fxa(
            dbsession, dupe_id, FirefoxAccountsInSchema(primary_email=alt_id_value)
        )
    if alt_id_name == "mofo_contact_id":
        create_mofo(
            dbsession,
            dupe_id,
            MozillaFoundationInSchema(
                mofo_email_id=str(uuid4()), mofo_contact_id=alt_id_value
            ),
        )

    create_newsletter(dbsession, dupe_id, NewsletterInSchema(name="zzz_sleepy_news"))
    create_newsletter(dbsession, dupe_id, NewsletterInSchema(name="aaa_game_news"))
    dbsession.flush()

    with StatementWatcher(dbsession.connection()) as watcher:
        contacts = get_contacts_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert watcher.count == 2
    assert len(contacts) == 2
    for contact in contacts:
        newsletter_names = [nl.name for nl in contact["newsletters"]]
        assert sorted(newsletter_names) == newsletter_names
