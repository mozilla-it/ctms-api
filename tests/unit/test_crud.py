"""Test database operations"""
# pylint: disable=too-many-lines
from datetime import datetime, timedelta, timezone
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
    get_stripe_customer_by_fxa_id,
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
)

# Treat all SQLAlchemy warnings as errors
pytestmark = pytest.mark.filterwarnings("error::sqlalchemy.exc.SAWarning")


def test_get_email(dbsession, email_factory):
    email = email_factory()
    dbsession.commit()

    fetched_email = get_email(dbsession, email.email_id)
    assert fetched_email.email_id == email.email_id


def test_get_email_with_stripe_customer(dbsession, stripe_customer_factory):
    stripe_customer = stripe_customer_factory()
    dbsession.commit()

    email = get_email(dbsession, stripe_customer.email.email_id)
    assert email.email_id == stripe_customer.email.email_id
    assert email.stripe_customer.stripe_id == stripe_customer.stripe_id


def test_get_email_with_stripe_subscription(dbsession, stripe_subscription_factory):
    subscription = stripe_subscription_factory()
    dbsession.commit()

    email_id = subscription.get_email_id()
    email = get_email(dbsession, email_id)
    assert subscription == email.stripe_customer.subscriptions[0]


def test_get_email_miss(dbsession):
    email = get_email(dbsession, str(uuid4()))
    assert email is None


def test_schedule_then_get_acoustic_records_before_time(dbsession, email_factory):
    email = email_factory()
    dbsession.flush()

    schedule_acoustic_record(dbsession, email.email_id)
    dbsession.commit()

    end_time = datetime.now(timezone.utc) + timedelta(hours=12)
    [record] = get_all_acoustic_records_before(
        dbsession,
        end_time=end_time,
    )
    assert record.email is not None
    assert record.retry is not None and record.retry == 0
    assert record.create_timestamp is not None
    assert record.update_timestamp is not None
    assert record.id is not None


def test_schedule_then_get_acoustic_records_as_contacts(dbsession, email_factory):
    email = email_factory()
    dbsession.commit()
    schedule_acoustic_record(dbsession, email.email_id)
    dbsession.commit()

    end_time = datetime.now(timezone.utc) + timedelta(hours=12)
    [record] = get_all_acoustic_records_before(
        dbsession,
        end_time=end_time,
    )
    [contact] = [get_contact_by_email_id(dbsession, record.email_id)]
    assert contact.email.email_id == record.email.email_id == email.email_id


def test_schedule_then_get_acoustic_records_retry_records(dbsession, email_factory):
    email = email_factory()
    dbsession.commit()
    schedule_acoustic_record(dbsession, email.email_id)
    dbsession.commit()

    end_time = datetime.now(timezone.utc) + timedelta(hours=12)
    [record] = get_all_acoustic_records_before(
        dbsession,
        end_time=end_time,
    )
    retry_acoustic_record(dbsession, record)

    dbsession.flush()

    [record] = get_all_acoustic_records_before(
        dbsession,
        end_time=end_time,
    )
    assert isinstance(record.email, Email)
    assert record.retry is not None and record.retry > 0
    assert record.create_timestamp != record.update_timestamp
    assert record.id is not None


def test_schedule_then_get_acoustic_records_minimum_retry(dbsession, email_factory):
    email = email_factory()
    dbsession.commit()
    schedule_acoustic_record(dbsession, email.email_id)
    dbsession.commit()

    end_time = datetime.now(timezone.utc) + timedelta(hours=12)
    [record] = get_all_acoustic_records_before(
        dbsession,
        end_time=end_time,
    )
    retry_acoustic_record(dbsession, record)
    dbsession.flush()

    record_list = get_all_acoustic_records_before(
        dbsession, end_time=end_time, retry_limit=1
    )
    assert len(record_list) == 0


def test_schedule_then_get_acoustic_records_then_delete(dbsession, email_factory):
    email = email_factory()
    dbsession.flush()
    schedule_acoustic_record(dbsession, email.email_id)
    dbsession.commit()

    end_time = datetime.now(timezone.utc) + timedelta(hours=12)
    [record] = get_all_acoustic_records_before(
        dbsession,
        end_time=end_time,
    )
    dbsession.commit()

    delete_acoustic_record(dbsession, record)
    dbsession.commit()

    record_list = get_all_acoustic_records_before(
        dbsession,
        end_time=end_time,
    )
    assert len(record_list) == 0


def retry_acoustic_record_with_error(dbsession, email_factory):
    email = email_factory()
    dbsession.commit()

    pending = PendingAcousticRecord(email_id=email.email_id)
    retry_acoustic_record(dbsession, pending, error_message="Boom!")
    dbsession.flush()

    assert (
        "Boom"
        in dbsession.query(PendingAcousticRecord)
        .filter(PendingAcousticRecord.email_id == email.email_id)
        .last_error
    )


def test_get_contact_by_email_id_found(dbsession, example_contact):
    email_id = example_contact.email.email_id
    contact = get_contact_by_email_id(dbsession, email_id)
    assert contact.email.email_id == email_id
    newsletter_names = [nl.name for nl in contact.newsletters]
    assert newsletter_names == ["firefox-welcome", "mozilla-welcome"]
    assert sorted(newsletter_names) == newsletter_names
    # `example_contact` has no associated stripe customer
    # We want to ensure we return an empty list specifically
    # pylint: disable-next=use-implicit-booleaness-not-comparison
    assert contact.products == []


def test_get_contact_by_email_id_miss(dbsession):
    contact = get_contact_by_email_id(dbsession, str(uuid4()))
    assert contact is None


def test_get_contact_by_email_id_stripe_customer_no_subscriptions(
    dbsession, stripe_customer_factory
):
    customer = stripe_customer_factory()
    dbsession.commit()

    contact = get_contact_by_email_id(dbsession, customer.get_email_id())
    # pylint: disable-next=use-implicit-booleaness-not-comparison
    assert contact.products == []


def test_get_contact_by_email_id_with_one_stripe_subscription(
    dbsession, stripe_subscription_factory
):
    """A contact with one Stripe subscription has one product."""
    subscription = stripe_subscription_factory()
    dbsession.commit()

    contact = get_contact_by_email_id(dbsession, subscription.get_email_id())
    assert len(contact.products) == 1
    price = subscription.subscription_items[0].price
    product = contact.products[0]
    assert product.dict() == {
        "payment_service": "stripe",
        "product_id": price.stripe_product_id,
        "segment": subscription.status,
        "changed": subscription.start_date,
        "sub_count": 1,
        "product_name": None,
        "price_id": price.stripe_id,
        "payment_type": None,
        "card_brand": None,
        "card_last4": None,
        "currency": price.currency,
        "amount": price.unit_amount,
        "billing_country": None,
        "status": subscription.status,
        "interval_count": price.recurring_interval_count,
        "interval": price.recurring_interval,
        "created": subscription.stripe_created,
        "start": subscription.start_date,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "canceled_at": None,
        "cancel_at_period_end": False,
        "ended_at": None,
    }


def test_get_contact_by_email_id_two_stripe_subscriptions(
    dbsession,
    stripe_customer_factory,
    stripe_subscription_factory,
):
    """A contact with two Stripe subscriptions to different products has two products."""
    customer = stripe_customer_factory()
    stripe_subscription_factory.create_batch(size=2, customer=customer)
    dbsession.commit()

    contact = get_contact_by_email_id(dbsession, customer.get_email_id())
    assert len(contact.products) == 2
    # pylint: disable-next=unbalanced-tuple-unpacking
    product1, product2 = contact.products
    assert product1 != product2


def test_get_contact_by_email_id_serial_stripe_subscriptions(
    dbsession,
    stripe_customer_factory,
    stripe_subscription_factory,
    stripe_price_factory,
):
    """A contact with two Stripe subscriptions to the same product has one product."""
    customer = stripe_customer_factory()
    price, another_price = stripe_price_factory.create_batch(
        size=2, stripe_product_id="prod_test"
    )
    stripe_subscription_factory(customer=customer, subscription_items__price=price)
    stripe_subscription_factory(
        customer=customer, subscription_items__price=another_price
    )
    dbsession.commit()

    contact = get_contact_by_email_id(dbsession, customer.get_email_id())
    assert len(contact.products) == 1
    product = contact.products[0]
    assert product.product_id == "prod_test"
    assert product.sub_count == 2
    assert product.segment == "re-active"


def test_get_contact_by_email_id_stripe_subscription_cancelled(
    dbsession, stripe_subscription_factory
):
    """A contact with a canceled Stripe subscription is in the canceled segement."""
    subscription = stripe_subscription_factory(status="canceled")
    subscription.ended_at = subscription.current_period_end
    dbsession.commit()

    email_id = subscription.get_email_id()
    pending = PendingAcousticRecord(email_id=email_id)
    contact = get_contact_by_email_id(dbsession, pending.email_id)
    assert len(contact.products) == 1
    product = contact.products[0]
    assert product.segment == "canceled"
    assert product.changed == subscription.ended_at


def test_get_contact_by_email_id_stripe_subscription_other(
    dbsession,
    stripe_subscription_factory,
):
    """A contact with a canceled Stripe subscription is in the canceled segement."""
    subscription = stripe_subscription_factory(status="unpaid")
    dbsession.commit()

    contact = get_contact_by_email_id(dbsession, subscription.get_email_id())
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
    newsletter_names = [nl.name for nl in contacts[0].newsletters]
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
        newsletter_names = [nl.name for nl in contact.newsletters]
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


class TestStripeRelations:
    """We don't use ForeignKeys for Stripe relations, because the object may come
    out of order for foreign key contraints. These tests help check that the manually
    created relationships are correct.

    When following a relationship, look for this warning in the logs:
    SAWarning: Multiple rows returned with uselist=False for lazily-loaded attribute

    This suggests that SQLAlchemy is joining tables without a limiting WHERE clause,
    and the first item will be returned rather than the related item.
    """

    @pytest.fixture(autouse=True)
    def stripe_customer_with_invoice(
        self, dbsession, stripe_customer_factory, stripe_invoice_factory
    ):
        """Creates a Stripe customer with:
        - two subscriptions, each with one subscription item
        - an invoice with two line items
          - each line item is associated with a separate subscription item
          - each (line item, subscription item) pair has 1 price associated with the pair

        This fixture is used so that we can verify the behavior of relationships below.

        These assertions also serve to validate the soundness of the Model factories. There
        is a lot baked into the relatively simple declaration of an invoice below.
        """

        stripe_customer = stripe_customer_factory()
        invoice = stripe_invoice_factory(customer=stripe_customer, line_items__size=2)
        dbsession.commit()

        assert stripe_customer.invoices == [invoice]
        assert len(invoice.line_items) == 2
        assert len(stripe_customer.subscriptions) == 2
        subscription_items = [
            sub_item
            for sub in stripe_customer.subscriptions
            for sub_item in sub.subscription_items
        ]
        assert len(subscription_items) == 2
        line_item_subscription_items = [
            line_item.subscription_item for line_item in invoice.line_items
        ]
        assert len(line_item_subscription_items) == 2
        assert subscription_items == line_item_subscription_items
        assert [sub_item.price for sub_item in subscription_items] == [
            line_item.price for line_item in invoice.line_items
        ]
        yield

    def test_email_relations_to_stripe_objects(
        self, dbsession, email_factory, stripe_customer_factory
    ):
        """Non-stripe objects have correct relations to Stripe objects."""

        email = email_factory(fxa=True)
        stripe_customer = stripe_customer_factory(fxa=email.fxa)
        dbsession.commit()

        assert email.stripe_customer == stripe_customer
        assert email.fxa.stripe_customer == stripe_customer

    def test_relations_on_stripe_customer(
        self,
        dbsession,
        email_factory,
        stripe_customer_factory,
        stripe_subscription_factory,
        stripe_invoice_factory,
    ):
        """StripeCustomer relationships are correct."""
        email = email_factory(fxa=True)
        stripe_customer = stripe_customer_factory(fxa=email.fxa)
        stripe_subscription = stripe_subscription_factory(customer=stripe_customer)
        stripe_invoice = stripe_invoice_factory(
            customer=stripe_customer,
            line_items__subscription_item=stripe_subscription.subscription_items[0],
        )
        dbsession.commit()
        assert stripe_customer.email == email
        assert stripe_customer.fxa == email.fxa
        assert stripe_customer.subscriptions == [stripe_subscription]
        assert stripe_customer.invoices == [stripe_invoice]
        assert stripe_customer.get_email_id() == email.email_id

    def test_relations_on_stripe_price(
        self,
        dbsession,
        stripe_price_factory,
        stripe_subscription_item_factory,
        stripe_invoice_line_item_factory,
    ):
        """StripePrice relations are correct."""
        price = stripe_price_factory()
        subscription_item = stripe_subscription_item_factory(price=price)
        line_item = stripe_invoice_line_item_factory(
            price=price, subscription_item=subscription_item
        )

        dbsession.commit()

        assert price.subscription_items == [subscription_item]
        assert price.invoice_line_items == [line_item]
        assert price.get_email_id() is None

    def test_relations_on_stripe_invoice(
        self,
        dbsession,
        email_factory,
        stripe_customer_factory,
        stripe_invoice_factory,
        stripe_invoice_line_item_factory,
    ):
        """StripeInvoice relations are correct."""
        email = email_factory(fxa=True)
        customer = stripe_customer_factory(fxa=email.fxa)
        invoice = stripe_invoice_factory(customer=customer, line_items=None)
        line_item = stripe_invoice_line_item_factory(invoice=invoice)
        dbsession.commit()

        assert invoice.get_email_id() == email.email_id
        assert invoice.customer == customer
        assert invoice.line_items == [line_item]

    def test_relations_on_stripe_invoice_line_items(
        self,
        dbsession,
        email_factory,
        stripe_customer_factory,
        stripe_price_factory,
        stripe_subscription_factory,
        stripe_subscription_item_factory,
        stripe_invoice_factory,
        stripe_invoice_line_item_factory,
    ):
        """StripeInvoiceLineItem relations are correct."""

        email = email_factory(fxa=True)
        customer = stripe_customer_factory(fxa=email.fxa)
        price = stripe_price_factory()
        subscription = stripe_subscription_factory(
            customer=customer, subscription_items=None
        )
        subscription_item = stripe_subscription_item_factory(
            subscription=subscription, price=price
        )
        invoice = stripe_invoice_factory(customer=customer, line_items=None)
        line_item = stripe_invoice_line_item_factory(
            invoice=invoice, subscription_item=subscription_item, price=price
        )
        dbsession.commit()

        assert line_item.invoice == invoice
        assert line_item.price == price
        assert line_item.subscription == subscription
        assert line_item.subscription_item == subscription_item
        assert line_item.get_email_id() == email.email_id

    def test_relations_on_stripe_subscription(
        self,
        dbsession,
        email_factory,
        stripe_customer_factory,
        stripe_subscription_factory,
        stripe_subscription_item_factory,
    ):
        """StripeSubscription relations are correct."""
        email = email_factory(fxa=True)
        customer = stripe_customer_factory(fxa=email.fxa)
        subscription = stripe_subscription_factory(
            customer=customer, subscription_items=None
        )
        subscription_item = stripe_subscription_item_factory(subscription=subscription)
        dbsession.commit()

        assert subscription.customer == customer
        assert subscription.subscription_items == [subscription_item]
        assert subscription.get_email_id() == email.email_id

    def test_relations_on_stripe_subscription_items(
        self,
        dbsession,
        email_factory,
        stripe_customer_factory,
        stripe_subscription_factory,
        stripe_subscription_item_factory,
        stripe_price_factory,
    ):
        """StripeSubscriptionItem relations are correct."""
        email = email_factory(fxa=True)
        customer = stripe_customer_factory(fxa=email.fxa)
        price = stripe_price_factory()
        subscription = stripe_subscription_factory(
            customer=customer, subscription_items=None
        )
        subscription_item = stripe_subscription_item_factory(
            subscription=subscription, price=price
        )
        dbsession.commit()

        assert subscription_item.subscription == subscription
        assert subscription_item.price == price
        assert subscription_item.get_email_id() == email.email_id


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
