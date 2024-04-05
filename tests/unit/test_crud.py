"""Test database operations"""
# pylint: disable=too-many-lines
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import sqlalchemy

from ctms.crud import (
    count_total_contacts,
    create_amo,
    create_email,
    create_fxa,
    create_mofo,
    create_newsletter,
    create_or_update_contact,
    get_bulk_contacts,
    get_contact_by_email_id,
    get_contacts_by_any_id,
    get_contacts_from_newsletter,
    get_contacts_from_waitlist,
    get_email,
    get_stripe_customer_by_fxa_id,
)
from ctms.database import ScopedSessionLocal
from ctms.models import Email
from ctms.schemas import (
    AddOnsInSchema,
    EmailInSchema,
    FirefoxAccountsInSchema,
    MozillaFoundationInSchema,
    NewsletterInSchema,
)
from ctms.schemas.contact import ContactPutSchema
from ctms.schemas.waitlist import WaitlistInSchema

# Treat all SQLAlchemy warnings as errors
pytestmark = pytest.mark.filterwarnings("error::sqlalchemy.exc.SAWarning")


def test_email_count(connection, email_factory):
    # The default `dbsession` fixture will run in a nested transaction
    # that is rollback.
    # In this test, we manipulate raw connections and transactions because
    # we need to force a VACUUM operation outside a running transaction.

    # Insert contacts in the table.
    transaction = connection.begin()
    session = ScopedSessionLocal()
    email_factory.create_batch(3)
    session.commit()
    session.close()
    transaction.commit()

    # Force an analysis of the table.
    old_isolation_level = connection.connection.isolation_level
    connection.connection.set_isolation_level(0)
    session.execute(sqlalchemy.text(f"VACUUM ANALYZE {Email.__tablename__}"))
    session.close()
    connection.connection.set_isolation_level(old_isolation_level)

    # Query the count result (since last analyze)
    session = ScopedSessionLocal()
    count = count_total_contacts(session)
    assert count == 3

    # Delete created objects (since our transaction was not rollback automatically)
    session.query(Email).delete()
    session.commit()
    session.close()


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
    contact = get_contact_by_email_id(dbsession, email_id)
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


@pytest.mark.parametrize(
    "mofo_relevant_flag,num_contacts_returned",
    [
        (None, 3),
        (True, 1),
        (False, 2),
    ],
)
def test_get_bulk_contacts_mofo_relevant(
    dbsession, email_factory, mofo_relevant_flag, num_contacts_returned
):
    email_factory()
    email_factory(mofo=True, mofo__mofo_relevant=True)
    email_factory(mofo=True, mofo__mofo_relevant=False)
    dbsession.commit()

    contacts = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=3,
        mofo_relevant=mofo_relevant_flag,
    )
    assert len(contacts) == num_contacts_returned


def test_get_bulk_contacts_time_bounds(dbsession, email_factory):
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(minutes=2)

    email_factory(update_timestamp=start_time - timedelta(minutes=1))
    targets = [
        email_factory(update_timestamp=start_time),
        email_factory(update_timestamp=start_time + timedelta(minutes=1)),
    ]
    email_factory(update_timestamp=end_time)
    email_factory(update_timestamp=end_time + timedelta(minutes=1))
    dbsession.commit()

    contacts = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=5,
    )

    assert len(contacts) == 2
    target_email_ids = [target.email_id for target in targets]
    contact_email_ids = [contact.email.email_id for contact in contacts]
    assert set(target_email_ids) == set(contact_email_ids)


def test_get_bulk_contacts_limited(dbsession, email_factory):
    email_factory.create_batch(10)
    dbsession.commit()

    contacts = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=5,
    )
    assert len(contacts) == 5


def test_get_bulk_contacts_after_email_id(dbsession, email_factory):
    first_email = email_factory()
    second_email = email_factory()
    dbsession.commit()

    [contact] = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=1,
        after_email_id=str(first_email.email_id),
    )
    assert contact.email.email_id != first_email.email_id
    assert contact.email.email_id == second_email.email_id


def test_get_bulk_contacts_one(dbsession, email_factory):
    email = email_factory()
    dbsession.commit()

    [contact] = get_bulk_contacts(
        dbsession,
        start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
        end_time=datetime.now(timezone.utc) + timedelta(minutes=1),
        limit=10,
    )
    assert contact.email.email_id == email.email_id


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


def test_create_or_update_contact_related_objects(dbsession, email_factory):
    email = email_factory(
        newsletters=3,
        waitlists=3,
    )
    dbsession.flush()

    new_source = "http://waitlists.example.com"
    putdata = ContactPutSchema(
        email=EmailInSchema(email_id=email.email_id, primary_email=email.primary_email),
        newsletters=[
            NewsletterInSchema(name=email.newsletters[0].name, source=new_source)
        ],
        waitlists=[WaitlistInSchema(name=email.waitlists[0].name, source=new_source)],
    )
    create_or_update_contact(dbsession, email.email_id, putdata, None)
    dbsession.commit()

    updated_email = dbsession.get(Email, email.email_id)
    # Existing related objects were deleted and replaced by the specified list.
    assert len(updated_email.newsletters) == 1
    assert len(updated_email.waitlists) == 1
    assert updated_email.newsletters[0].source == new_source
    assert updated_email.waitlists[0].source == new_source


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


def test_create_or_update_contact_timestamps(dbsession, email_factory):
    email = email_factory(
        newsletters=1,
        waitlists=1,
    )
    dbsession.flush()

    before_nl = email.newsletters[0].update_timestamp
    before_wl = email.waitlists[0].update_timestamp

    new_source = "http://waitlists.example.com"
    putdata = ContactPutSchema(
        email=EmailInSchema(email_id=email.email_id, primary_email=email.primary_email),
        newsletters=[
            NewsletterInSchema(name=email.newsletters[0].name, source=new_source)
        ],
        waitlists=[WaitlistInSchema(name=email.waitlists[0].name, source=new_source)],
    )
    create_or_update_contact(dbsession, email.email_id, putdata, None)
    dbsession.commit()

    updated_email = get_email(dbsession, email.email_id)
    assert updated_email.newsletters[0].update_timestamp > before_nl
    assert updated_email.waitlists[0].update_timestamp > before_wl


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
