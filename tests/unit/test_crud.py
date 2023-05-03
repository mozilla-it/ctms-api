"""Test database operations"""
# pylint: disable=too-many-lines
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import uuid4

import pytest
import sqlalchemy
from sqlalchemy.orm import Session

from ctms.crud import (
    create_acoustic_field,
    create_acoustic_newsletters_mapping,
    create_amo,
    create_email,
    create_fxa,
    create_mofo,
    create_newsletter,
    create_stripe_customer,
    create_stripe_invoice,
    create_stripe_invoice_line_item,
    create_stripe_price,
    create_stripe_subscription,
    create_stripe_subscription_item,
    delete_acoustic_field,
    delete_acoustic_newsletters_mapping,
    delete_acoustic_record,
    get_all_acoustic_fields,
    get_all_acoustic_records_before,
    get_bulk_contacts,
    get_contact_by_email_id,
    get_contacts_by_any_id,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
    get_email,
    get_emails_by_any_id,
    get_stripe_customer_by_fxa_id,
    get_stripe_subscription_by_stripe_id,
    retry_acoustic_record,
    schedule_acoustic_record,
)
from ctms.models import (
    AcousticField,
    AcousticNewsletterMapping,
    Email,
    PendingAcousticRecord,
)
from ctms.schemas import (
    AddOnsInSchema,
    EmailInSchema,
    FirefoxAccountsInSchema,
    MozillaFoundationInSchema,
    NewsletterInSchema,
    StripeCustomerCreateSchema,
    StripeInvoiceCreateSchema,
    StripeInvoiceLineItemCreateSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)
from tests.data import fake_stripe_id
from tests.unit.conftest import FAKE_STRIPE_CUSTOMER_ID

# Treat all SQLAlchemy warnings as errors
pytestmark = pytest.mark.filterwarnings("error::sqlalchemy.exc.SAWarning")


def test_get_email(dbsession, example_contact):
    email_id = example_contact.email.email_id
    email = get_email(dbsession, email_id)
    assert email.email_id == email_id

    newsletter_names = [newsletter.name for newsletter in email.newsletters]
    assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
    assert sorted(newsletter_names) == newsletter_names

    waitlists_names = [waitlist.name for waitlist in email.waitlists]
    assert waitlists_names == ["example-product", "relay", "vpn"]
    assert sorted(waitlists_names) == waitlists_names


def test_get_email_with_stripe_customer(dbsession, stripe_customer_factory):
    stripe_customer = stripe_customer_factory()
    dbsession.commit()

    email = get_email(dbsession, stripe_customer.email.email_id)
    assert email.email_id == stripe_customer.email.email_id
    assert email.stripe_customer.stripe_id == stripe_customer.stripe_id


def test_get_email_with_stripe_subscription(
    dbsession, contact_with_stripe_subscription, stripe_price_data
):
    """`stripe_price_data` is used when building `contact_with_stripe_subscription`"""
    email_id = contact_with_stripe_subscription.email.email_id
    email = get_email(dbsession, email_id)
    assert email.email_id == email_id

    newsletter_names = [newsletter.name for newsletter in email.newsletters]
    assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
    assert sorted(newsletter_names) == newsletter_names

    assert email.stripe_customer.stripe_id == FAKE_STRIPE_CUSTOMER_ID
    assert len(email.stripe_customer.subscriptions) == 1
    assert len(email.stripe_customer.subscriptions[0].subscription_items) == 1
    assert (
        email.stripe_customer.subscriptions[0].subscription_items[0].price.stripe_id
        == stripe_price_data["stripe_id"]
    )


def test_get_email_miss(dbsession):
    email = get_email(dbsession, str(uuid4()))
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
    emails = get_emails_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert len(emails) == 1
    newsletter_names = [newsletter.name for newsletter in emails[0].newsletters]
    assert sorted(newsletter_names) == newsletter_names


def test_get_emails_by_any_id_missing(dbsession):
    emails = get_emails_by_any_id(dbsession, basket_token=str(uuid4()))
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

    emails = get_emails_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert len(emails) == 2
    for email in emails:
        newsletter_names = [newsletter.name for newsletter in email.newsletters]
        assert sorted(newsletter_names) == newsletter_names


def test_get_contact_by_email_id_found(dbsession, example_contact):
    email_id = example_contact.email.email_id
    contact = get_contact_by_email_id(dbsession, email_id)
    assert contact.email.email_id == email_id
    newsletter_names = [nl.name for nl in contact.newsletters]
    assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
    assert sorted(newsletter_names) == newsletter_names
    # We want to ensure we return an empty list specifically
    # pylint: disable-next=use-implicit-booleaness-not-comparison
    assert contact.products == []


def test_get_contact_by_email_id_miss(dbsession):
    contact = get_contact_by_email_id(dbsession, str(uuid4()))
    assert contact is None


def test_schedule_then_get_acoustic_records_before_time(
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
    contact_record_list = [
        get_contact_by_email_id(dbsession, record.email_id) for record in record_list
    ]
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
    assert len(record_list) == 0


def test_schedule_then_get_acoustic_records_then_delete(
    dbsession, example_contact, maximal_contact, minimal_contact
):
    contact_list = [example_contact, maximal_contact, minimal_contact]
    end_time = datetime.now(timezone.utc) + timedelta(hours=12)

    for record in contact_list:
        schedule_acoustic_record(dbsession, record.email.email_id)

    dbsession.flush()

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
    assert len(record_list) == 0


def retry_acoustic_record_with_error(dbsession, example_contact):
    pending = PendingAcousticRecord(email_id=example_contact.email.email_id)
    retry_acoustic_record(dbsession, pending, error_message="Boom!")
    dbsession.flush()

    assert (
        "Boom"
        in dbsession.query(PendingAcousticRecord)
        .filter(PendingAcousticRecord.email_id == example_contact.email.email_id)
        .last_error
    )


def test_get_acoustic_record_no_stripe_customer(dbsession, example_contact):
    """A contact with no associated Stripe customer has no subscriptions."""
    pending = PendingAcousticRecord(email_id=example_contact.email.email_id)
    contact = get_contact_by_email_id(dbsession, pending.email_id)
    assert not contact.products


def test_get_acoustic_record_no_stripe_subscriptions(
    dbsession, stripe_customer_factory
):
    """A contact with no Stripe subscriptions has no subscriptions."""
    stripe_customer = stripe_customer_factory()
    dbsession.commit()

    email_id = stripe_customer.email.email_id
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_contact_by_email_id(dbsession, pending.email_id)
    assert not contact.products


def test_get_acoustic_record_one_stripe_subscription(
    dbsession, contact_with_stripe_subscription
):
    """A contact with one Stripe subscription has one product."""
    email_id = contact_with_stripe_subscription.email.email_id
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_contact_by_email_id(dbsession, pending.email_id)
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
    dbsession,
    contact_with_stripe_subscription,
    stripe_price_data,
    stripe_subscription_data,
    stripe_subscription_item_data,
):
    """A contact with two Stripe subscriptions to different products has two products."""
    email_id = contact_with_stripe_subscription.email.email_id
    now = datetime.now(tz=timezone.utc)
    new_subscription = stripe_subscription_data
    new_sub_item = stripe_subscription_item_data
    new_price = stripe_price_data
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
    contact = get_contact_by_email_id(dbsession, pending.email_id)
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
    dbsession,
    contact_with_stripe_subscription,
    stripe_subscription_data,
    stripe_subscription_item_data,
):
    """A contact with two Stripe subscriptions to the same product has one product."""
    email_id = contact_with_stripe_subscription.email.email_id
    old_subscription = stripe_subscription_data
    old_sub_item = stripe_subscription_item_data
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
    contact = get_contact_by_email_id(dbsession, pending.email_id)
    assert len(contact.products) == 1
    product = contact.products[0]
    assert product.product_id == "prod_cHJvZHVjdA"
    assert product.sub_count == 2
    assert product.segment == "re-active"


def test_get_acoustic_record_stripe_subscription_cancelled(
    dbsession, contact_with_stripe_subscription, stripe_subscription_data
):
    """A contact with a canceled Stripe subscription is in the canceled segement."""
    subscription = get_stripe_subscription_by_stripe_id(
        dbsession, stripe_subscription_data["stripe_id"]
    )
    subscription.status = "canceled"
    subscription.ended_at = subscription.current_period_end
    dbsession.commit()
    email_id = contact_with_stripe_subscription.email.email_id
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_contact_by_email_id(dbsession, pending.email_id)
    assert len(contact.products) == 1
    product = contact.products[0]
    assert product.segment == "canceled"
    assert product.changed == subscription.ended_at


def test_get_acoustic_record_stripe_subscription_other(
    dbsession, contact_with_stripe_subscription, stripe_subscription_data
):
    """A contact with a canceled Stripe subscription is in the canceled segement."""
    subscription = get_stripe_subscription_by_stripe_id(
        dbsession, stripe_subscription_data["stripe_id"]
    )
    subscription.status = "unpaid"
    dbsession.commit()
    email_id = contact_with_stripe_subscription.email.email_id
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_contact_by_email_id(dbsession, pending.email_id)
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

    bulk_contact_list = get_bulk_contacts(
        dbsession,
        start_time=after_start,
        end_time=end_time,
        limit=10,
        mofo_relevant=mofo_relevant_flag,
    )
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
    bulk_contact_list = get_bulk_contacts(
        dbsession,
        start_time=after_start,
        end_time=end_time,
        limit=10,
        mofo_relevant=mofo_relevant_flag,
    )
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
    bulk_contact_list = get_bulk_contacts(
        dbsession,
        start_time=after_start,
        end_time=end_time,
        limit=2,
        after_email_id=after_id,
    )
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

    bulk_contact_list = get_bulk_contacts(
        dbsession,
        start_time=after_start,
        end_time=end_time,
        limit=1,
        after_email_id=after_id,
    )
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

    bulk_contact_list = get_bulk_contacts(
        dbsession,
        start_time=timestamp,
        end_time=datetime.now(timezone.utc),
        limit=10,
    )
    assert len(bulk_contact_list) >= 3
    assert example_contact in bulk_contact_list
    assert maximal_contact in bulk_contact_list
    assert minimal_contact in bulk_contact_list


def test_get_bulk_contacts_one(dbsession, example_contact):
    email_id = example_contact.email.email_id
    timestamp: datetime = example_contact.email.update_timestamp
    start_time = timestamp - timedelta(12)
    end_time = timestamp + timedelta(hours=12)

    bulk_contact_list = get_bulk_contacts(
        dbsession, start_time=start_time, end_time=end_time, limit=10
    )
    assert len(bulk_contact_list) == 1
    assert bulk_contact_list[0].email.email_id == email_id


def test_get_bulk_contacts_none(dbsession):
    bulk_contact_list = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1),
        limit=10,
    )
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
    contacts = get_contacts_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert len(contacts) == 1
    newsletter_names = [nl.name for nl in contacts[0]["newsletters"]]
    assert sorted(newsletter_names) == newsletter_names


def test_get_contact_by_any_id_missing(dbsession, sample_contacts):
    contact = get_contacts_by_any_id(dbsession, basket_token=str(uuid4()))
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

    contacts = get_contacts_by_any_id(dbsession, **{alt_id_name: alt_id_value})
    assert len(contacts) == 2
    for contact in contacts:
        newsletter_names = [nl.name for nl in contact["newsletters"]]
        assert sorted(newsletter_names) == newsletter_names


@pytest.mark.parametrize("with_lock", (True, False))
def test_get_stripe_customer_by_existing_fxa_id(
    dbsession, with_lock, stripe_customer_factory
):
    """A StripeCustomer can be fetched by an existing fxa_id."""
    stripe_customer = stripe_customer_factory()
    dbsession.commit()

    fxa_id = stripe_customer.fxa.fxa_id
    customer = get_stripe_customer_by_fxa_id(dbsession, fxa_id, for_update=with_lock)
    assert customer.fxa_id == fxa_id


@pytest.mark.parametrize("with_lock", (True, False))
def test_get_stripe_customer_by_nonexistent_fxa_id(
    dbsession, with_lock, stripe_customer_factory
):
    """A StripeCustomer with a nonexistent fx_id should not exist."""
    # So we know that there's at least some stripe customer data
    stripe_customer_factory()
    dbsession.commit()

    fxa_id = str(uuid4().hex)
    customer = get_stripe_customer_by_fxa_id(dbsession, fxa_id, for_update=with_lock)
    assert customer is None


@pytest.fixture()
def stripe_objects(
    dbsession,
    example_contact,
    maximal_contact,
    stripe_price_data,
    stripe_subscription_data,
    stripe_subscription_item_data,
    stripe_invoice_data,
    stripe_invoice_line_item_data,
):
    """
    Create two complete trees of Stripe objects.

    We don't use ForeignKeys for Stripe relations, because the object may come
    out of order for foreign key contraints. This helps check that the manually
    created relationships are correct.

    When following a relationship, look for this warning in the logs:
    SAWarning: Multiple rows returned with uselist=False for lazily-loaded attribute

    This suggests that SQLAlchemy is joining tables without a limiting WHERE clause,
    and the first item will be returned rather than the related item.
    """
    # Create prices / products
    # Both customers are subscribed to all four, 2 per subscription
    prices = []
    for price_idx in range(4):
        price_data = stripe_price_data
        price_data["stripe_id"] = fake_stripe_id("price", f"price_{price_idx}")
        price_data["stripe_product_id"] = fake_stripe_id("prod", f"prod_{price_idx}")
        prices.append(
            create_stripe_price(dbsession, StripePriceCreateSchema(**price_data))
        )

    objs = []
    for contact_idx, contact in enumerate((example_contact, maximal_contact)):
        email_id = contact.email.email_id
        email = get_email(dbsession, email_id)
        obj = {
            "email_id": email_id,
            "contact": email,
            "customer": None,
            "subscription": [],
            "invoice": [],
        }
        objs.append(obj)

        # Create Customer data
        customer_stripe_id = fake_stripe_id("cus", f"cus_{contact_idx}")
        obj["customer"] = create_stripe_customer(
            dbsession,
            StripeCustomerCreateSchema(
                stripe_id=customer_stripe_id,
                stripe_created=datetime.now(timezone.utc),
                fxa_id=contact.fxa.fxa_id,
                default_source_id=None,
                invoice_settings_default_payment_method_id=fake_stripe_id(
                    "pm", "payment_method"
                ),
            ),
        )

        # Create Subscriptions / Invoices and related items
        for sub_inv_idx in range(2):
            sub_data = stripe_subscription_data
            sub_data["stripe_id"] = fake_stripe_id(
                "sub", f"cus_{contact_idx}_sub_{sub_inv_idx}"
            )
            sub_data["stripe_customer_id"] = customer_stripe_id
            sub_obj = {
                "obj": create_stripe_subscription(
                    dbsession, StripeSubscriptionCreateSchema(**sub_data)
                ),
                "items": [],
            }
            obj["subscription"].append(sub_obj)

            inv_data = stripe_invoice_data
            inv_data["stripe_id"] = fake_stripe_id(
                "sub", f"cus_{contact_idx}_inv_{sub_inv_idx}"
            )
            inv_data["stripe_customer_id"] = customer_stripe_id
            inv_obj = {
                "obj": create_stripe_invoice(
                    dbsession, StripeInvoiceCreateSchema(**inv_data)
                ),
                "line_items": [],
            }
            obj["invoice"].append(inv_obj)

            for item_idx in range(2):
                price = prices[sub_inv_idx * 2 + item_idx]

                si_data = stripe_subscription_item_data
                si_data["stripe_id"] = fake_stripe_id(
                    "si", f"cus_{contact_idx}_sub_{sub_inv_idx}_si_{item_idx}"
                )
                si_data["stripe_price_id"] = price.stripe_id
                si_data["stripe_subscription_id"] = sub_data["stripe_id"]
                sub_obj["items"].append(
                    {
                        "obj": create_stripe_subscription_item(
                            dbsession, StripeSubscriptionItemCreateSchema(**si_data)
                        ),
                        "price": price,
                    }
                )

                li_data = stripe_invoice_line_item_data
                li_data["stripe_id"] = fake_stripe_id(
                    "il", f"cus_{contact_idx}_inv_{sub_inv_idx}_il_{item_idx}"
                )
                li_data["stripe_invoice_id"] = inv_data["stripe_id"]
                li_data["stripe_price_id"] = price.stripe_id
                li_data["stripe_subscription_id"] = sub_data["stripe_id"]
                li_data["stripe_subscription_item_id"] = si_data["stripe_id"]
                inv_obj["line_items"].append(
                    {
                        "obj": create_stripe_invoice_line_item(
                            dbsession, StripeInvoiceLineItemCreateSchema(**li_data)
                        ),
                        "price": price,
                    }
                )
    dbsession.commit()
    return objs


@pytest.mark.parametrize("contact_idx", range(2))
def test_relations_to_stripe_objects(stripe_objects, contact_idx):
    """Non-stripe objects have correct relations to Stripe objects."""
    contact = stripe_objects[contact_idx]["contact"]
    customer = stripe_objects[contact_idx]["customer"]

    assert contact.stripe_customer == customer
    assert contact.fxa.stripe_customer == customer


@pytest.mark.parametrize("contact_idx", range(2))
def test_relations_on_stripe_customer(stripe_objects, contact_idx):
    """StripeCustomer relationships are correct."""
    contact = stripe_objects[contact_idx]
    email = contact["contact"]
    email_id = contact["email_id"]
    customer = contact["customer"]
    invoices = set(inv["obj"] for inv in contact["invoice"])
    subscriptions = set(sub["obj"] for sub in contact["subscription"])

    assert customer.email == email
    assert customer.fxa == email.fxa
    assert set(customer.invoices) == invoices
    assert set(customer.subscriptions) == subscriptions
    assert customer.get_email_id() == email_id


@pytest.mark.parametrize("si_idx", range(2))
@pytest.mark.parametrize("item_idx", range(2))
def test_relations_on_stripe_price(stripe_objects, si_idx, item_idx):
    """StripePrice relations are correct."""
    price = None
    subscription_items = set()
    invoice_line_items = set()
    for contact in stripe_objects:
        subscription_item = contact["subscription"][si_idx]["items"][item_idx]
        if price:
            assert subscription_item["price"] == price
        else:
            price = subscription_item["price"]
        subscription_items.add(subscription_item["obj"])

        invoice_line_item = contact["invoice"][si_idx]["line_items"][item_idx]
        assert invoice_line_item["price"] == price
        invoice_line_items.add(invoice_line_item["obj"])

    assert set(price.invoice_line_items) == invoice_line_items
    assert set(price.subscription_items) == subscription_items
    assert price.get_email_id() is None


@pytest.mark.parametrize("contact_idx", range(2))
@pytest.mark.parametrize("inv_idx", range(2))
def test_relations_on_stripe_invoice(stripe_objects, contact_idx, inv_idx):
    """StripeInvoice relations are correct."""
    contact = stripe_objects[contact_idx]
    customer = contact["customer"]
    email_id = contact["email_id"]
    invoice = contact["invoice"][inv_idx]["obj"]
    line_items = set(item["obj"] for item in contact["invoice"][inv_idx]["line_items"])

    assert invoice.customer == customer
    assert set(invoice.line_items) == line_items
    assert invoice.get_email_id() == email_id


@pytest.mark.parametrize("contact_idx", range(2))
@pytest.mark.parametrize("inv_idx", range(2))
@pytest.mark.parametrize("li_idx", range(2))
def test_relations_on_stripe_invoice_line_items(
    stripe_objects, contact_idx, inv_idx, li_idx
):
    """StripeInvoiceLineItem relations are correct."""
    contact = stripe_objects[contact_idx]
    email_id = contact["email_id"]
    inv_data = contact["invoice"][inv_idx]
    invoice = inv_data["obj"]
    line_item = inv_data["line_items"][li_idx]["obj"]
    price = inv_data["line_items"][li_idx]["price"]
    sub_data = contact["subscription"][inv_idx]
    subscription = sub_data["obj"]
    subscription_item = sub_data["items"][li_idx]["obj"]
    assert sub_data["items"][li_idx]["price"] == price

    assert line_item.invoice == invoice
    assert line_item.price == price
    assert line_item.subscription == subscription
    assert line_item.subscription_item == subscription_item
    assert line_item.get_email_id() == email_id


@pytest.mark.parametrize("contact_idx", range(2))
@pytest.mark.parametrize("sub_idx", range(2))
def test_relations_on_stripe_subscription(stripe_objects, contact_idx, sub_idx):
    """StripeSubscription relations are correct."""
    contact = stripe_objects[contact_idx]
    customer = contact["customer"]
    email_id = contact["email_id"]
    subscription = contact["subscription"][sub_idx]["obj"]
    items = set(item["obj"] for item in contact["subscription"][sub_idx]["items"])

    assert subscription.customer == customer
    assert set(subscription.subscription_items) == items
    assert subscription.get_email_id() == email_id


@pytest.mark.parametrize("contact_idx", range(2))
@pytest.mark.parametrize("sub_idx", range(2))
@pytest.mark.parametrize("si_idx", range(2))
def test_relations_on_stripe_subscription_items(
    stripe_objects, contact_idx, sub_idx, si_idx
):
    """StripeSubscriptionItem relations are correct."""
    contact = stripe_objects[contact_idx]
    email_id = contact["email_id"]
    sub_data = contact["subscription"][sub_idx]
    subscription = sub_data["obj"]
    subscription_item = sub_data["items"][si_idx]["obj"]
    price = sub_data["items"][si_idx]["price"]

    assert subscription_item.subscription == subscription
    assert subscription_item.price == price
    assert subscription_item.get_email_id() == email_id


def test_get_contacts_from_newsletter(dbsession, newsletter_factory):
    existing_newsletter = newsletter_factory()
    dbsession.flush()
    contacts = get_contacts_from_newsletter(dbsession, existing_newsletter.name)
    assert len(contacts) == 1
    assert contacts[0].email.email_id == existing_newsletter.email.email_id


def test_get_contacts_from_waitlist(dbsession, waitlist_factory):
    existing_waitlist = waitlist_factory()
    dbsession.flush()
    contacts = get_contacts_from_waitlist(dbsession, existing_waitlist.name)
    assert len(contacts) == 1
    assert contacts[0].email.email_id == existing_waitlist.email.email_id


def test_create_acoustic_field(dbsession: Session):
    fields = dbsession.query(AcousticField).filter_by(tablename="main")
    main_fields = {f.field for f in fields}
    assert "sub_test_field" not in main_fields

    create_acoustic_field(dbsession, "main", "sub_test_field")
    dbsession.commit()

    main_fields = {f.field for f in fields}
    assert "sub_test_field" in main_fields


def test_create_acoustic_field_same_pkey_does_not_raise(dbsession: Session):
    # though there is a composite primary key on tablename + field, attempting
    # to add the same tablename + field does not raise an exception
    create_acoustic_field(dbsession, "main", "sub_test_field")
    create_acoustic_field(dbsession, "main", "sub_test_field")


def test_delete_acoustic_field(dbsession):
    fields = dbsession.query(AcousticField)
    assert ("main", "email") in [(f.tablename, f.field) for f in fields]

    deleted = delete_acoustic_field(dbsession, "main", "email")

    assert (deleted.tablename, deleted.field) == ("main", "email")
    assert ("main", "email") not in [(f.tablename, f.field) for f in fields]


def test_delete_acoustic_field_no_field_present(dbsession):
    fields = dbsession.query(AcousticField)
    assert ("foo", "bar") not in [(f.tablename, f.field) for f in fields]

    deleted = delete_acoustic_field(dbsession, "foo", "bar")
    assert deleted is None


def test_get_all_acoustic_fields(dbsession):
    assert (
        len(get_all_acoustic_fields(dbsession))
        == dbsession.query(AcousticField).count()
    )


def test_get_all_acoustic_fields_filter_by_tablename(dbsession):
    dbsession.add(AcousticField(tablename="test", field="test"))
    dbsession.flush()
    num_fields = dbsession.query(AcousticField).count()
    num_main_fields = len(get_all_acoustic_fields(dbsession, tablename="main"))
    assert num_fields > num_main_fields


def test_create_acoustic_newsletters_mapping(dbsession, acoustic_newsletters_mapping):
    new_mapping = create_acoustic_newsletters_mapping(dbsession, "test", "sub_test")
    assert (new_mapping.source, new_mapping.destination) == ("test", "sub_test")
    all_mappings_count = dbsession.query(AcousticNewsletterMapping).count()
    assert all_mappings_count > len(acoustic_newsletters_mapping)


def test_create_acoustic_newsletters_mapping_duplicate_mapping(dbsession):
    create_acoustic_newsletters_mapping(dbsession, "test", "sub_test")
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        create_acoustic_newsletters_mapping(dbsession, "test", "sub_test")


def test_create_acoustic_newsletters_mapping_source_to_many_dest(dbsession):
    create_acoustic_newsletters_mapping(dbsession, "test", "sub_test")
    create_acoustic_newsletters_mapping(dbsession, "test2", "sub_test")


def test_delete_acoustic_newsletters_mapping(dbsession, acoustic_newsletters_mapping):
    mappings = list(acoustic_newsletters_mapping.items())
    (sample_source, sample_destination) = mappings[0]

    deleted_mapping = delete_acoustic_newsletters_mapping(dbsession, sample_source)

    assert (deleted_mapping.source, deleted_mapping.destination) == (
        sample_source,
        sample_destination,
    )
    all_mappings_count = dbsession.query(AcousticNewsletterMapping).count()
    assert all_mappings_count < len(acoustic_newsletters_mapping)


def test_delete_acoustic_newsletters_mapping_no_mapping(
    dbsession, acoustic_newsletters_mapping
):
    deleted_mapping = delete_acoustic_newsletters_mapping(
        dbsession, "no_mapping_for_this_source"
    )

    assert deleted_mapping is None
    all_mappings_count = dbsession.query(AcousticNewsletterMapping).count()
    assert all_mappings_count == len(acoustic_newsletters_mapping)
