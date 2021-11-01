"""Test ingesting of Stripe data"""

from __future__ import annotations

import json
import os.path
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from time import mktime
from typing import Dict, Optional
from uuid import uuid4

import pytest

from ctms.crud import (
    create_email,
    create_stripe_customer,
    create_stripe_price,
    create_stripe_subscription,
    create_stripe_subscription_item,
    get_contact_by_email_id,
)
from ctms.ingest_stripe import (
    StripeIngestBadObjectError,
    StripeIngestUnknownObjectError,
    ingest_stripe_customer,
    ingest_stripe_object,
    ingest_stripe_price,
    ingest_stripe_subscription,
)
from ctms.schemas import (
    EmailInSchema,
    StripeCustomerCreateSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)


def fake_stripe_id(prefix: str, seed: str, suffix: Optional[str] = None) -> str:
    """Create a fake Stripe ID for testing"""
    body = b64encode(seed.encode()).decode().replace("=", "")
    return f"{prefix}_{body}{suffix if suffix else ''}"


# Documentation and test Stripe IDs
FAKE_CUSTOMER_ID = fake_stripe_id("cus", "customer")
FAKE_INVOICE_ID = fake_stripe_id("in", "invoice")
FAKE_PAYMENT_METHOD_ID = fake_stripe_id("pm", "payment_method")
FAKE_PRICE_ID = fake_stripe_id("price", "price")
FAKE_PRODUCT_ID = fake_stripe_id("prod", "product")
FAKE_SUBSCRIPTION_ID = fake_stripe_id("sub", "subscription")
FAKE_SUBSCRIPTION_ITEM_ID = fake_stripe_id("si", "subscription_item")


def unix_timestamp(the_time: Optional[datetime] = None) -> int:
    """Create a UNIX timestamp from a datetime or now"""
    the_time = the_time or datetime.now(tz=timezone.utc)
    return int(mktime(the_time.timetuple()))


def stripe_customer_data() -> Dict:
    """Return minimal Stripe customer data."""
    fxa_id = str(uuid4())
    return {
        "id": FAKE_CUSTOMER_ID,
        "object": "customer",
        "created": unix_timestamp(datetime(2021, 10, 25, 15, 34, tzinfo=timezone.utc)),
        "description": fxa_id,
        "email": "fxa_email@example.com",
        "default_source": None,
        "invoice_settings": {
            "default_payment_method": FAKE_PAYMENT_METHOD_ID,
        },
    }


@pytest.fixture
def stripe_customer(dbsession, example_contact):
    """Return a Stripe Customer associated with the example contact."""
    schema = StripeCustomerCreateSchema(
        stripe_id=FAKE_CUSTOMER_ID,
        stripe_created=datetime(2021, 10, 25, 15, 34, tzinfo=timezone.utc),
        email_id=example_contact.email.email_id,
        default_source_id=None,
        invoice_settings_default_payment_method_id=FAKE_PAYMENT_METHOD_ID,
    )
    customer = create_stripe_customer(dbsession, schema)
    dbsession.commit()
    dbsession.refresh(customer)
    return customer


def stripe_subscription_data() -> Dict:
    """Return minimal Stripe subscription data."""
    return {
        "id": FAKE_SUBSCRIPTION_ID,
        "object": "subscription",
        "created": unix_timestamp(datetime(2021, 9, 27, tzinfo=timezone.utc)),
        "customer": FAKE_CUSTOMER_ID,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "current_period_start": unix_timestamp(
            datetime(2021, 10, 27, tzinfo=timezone.utc)
        ),
        "current_period_end": unix_timestamp(
            datetime(2021, 11, 27, tzinfo=timezone.utc)
        ),
        "ended_at": None,
        "start_date": unix_timestamp(datetime(2021, 9, 27, tzinfo=timezone.utc)),
        "status": "active",
        "default_source": None,
        "default_payment_method": None,
        "items": {
            "object": "list",
            "total_count": 1,
            "has_more": False,
            "url": f"/v1/subscription_items?subscription={FAKE_SUBSCRIPTION_ID}",
            "data": [
                {
                    "id": FAKE_SUBSCRIPTION_ITEM_ID,
                    "object": "subscription_item",
                    "created": unix_timestamp(
                        datetime(2021, 9, 27, tzinfo=timezone.utc)
                    ),
                    "subscription": FAKE_SUBSCRIPTION_ID,
                    "price": stripe_price_data(),
                }
            ],
        },
    }


@pytest.fixture
def stripe_subscription(dbsession, stripe_price):
    subscription = StripeSubscriptionCreateSchema(
        stripe_id=FAKE_SUBSCRIPTION_ID,
        stripe_created=datetime(2021, 9, 27, tzinfo=timezone.utc),
        stripe_customer_id=FAKE_CUSTOMER_ID,
        cancel_at_period_end=True,
        canceled_at=None,
        current_period_start=datetime(2021, 10, 27, tzinfo=timezone.utc),
        current_period_end=datetime(2021, 11, 27, tzinfo=timezone.utc),
        ended_at=None,
        start_date=datetime(2021, 9, 27, tzinfo=timezone.utc),
        status="active",
    )
    db_subscription = create_stripe_subscription(dbsession, subscription)
    subscription_item = StripeSubscriptionItemCreateSchema(
        stripe_id=FAKE_SUBSCRIPTION_ITEM_ID,
        stripe_created=datetime(2021, 9, 27, tzinfo=timezone.utc),
        stripe_subscription_id=FAKE_SUBSCRIPTION_ID,
        stripe_price_id=FAKE_PRICE_ID,
    )
    db_subscription_item = create_stripe_subscription_item(dbsession, subscription_item)
    assert db_subscription_item

    dbsession.commit()
    dbsession.refresh(db_subscription)
    return db_subscription


def stripe_price_data() -> Dict:
    """Return minimal Stripe price data."""
    return {
        "id": FAKE_PRICE_ID,
        "object": "price",
        "created": unix_timestamp(datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc)),
        "product": FAKE_PRODUCT_ID,
        "active": True,
        "currency": "usd",
        "recurring": {
            "interval": "month",
            "interval_count": 1,
        },
        "unit_amount": 999,
    }


@pytest.fixture
def stripe_price(dbsession):
    price = StripePriceCreateSchema(
        stripe_id=FAKE_PRICE_ID,
        stripe_created=datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc),
        stripe_product_id=FAKE_PRODUCT_ID,
        currency="usd",
        recurring_interval="month",
        recurring_interval_count=1,
        unit_amount=999,
    )
    db_price = create_stripe_price(dbsession, price)
    assert db_price
    dbsession.commit()
    dbsession.refresh(db_price)
    return db_price


def test_ids():
    """Get the fake IDs, to make it easier to copy to schemas."""
    assert FAKE_CUSTOMER_ID == "cus_Y3VzdG9tZXI"
    assert FAKE_INVOICE_ID == "in_aW52b2ljZQ"
    assert FAKE_PAYMENT_METHOD_ID == "pm_cGF5bWVudF9tZXRob2Q"
    assert FAKE_PRICE_ID == "price_cHJpY2U"
    assert FAKE_PRODUCT_ID == "prod_cHJvZHVjdA"
    assert FAKE_SUBSCRIPTION_ID == "sub_c3Vic2NyaXB0aW9u"
    assert FAKE_SUBSCRIPTION_ITEM_ID == "si_c3Vic2NyaXB0aW9uX2l0ZW0"


def test_ingest_existing_contact(dbsession, example_contact):
    """A Stripe Customer is associated with the existing contact."""
    data = stripe_customer_data()
    data["description"] = example_contact.fxa.fxa_id
    data["email"] = example_contact.fxa.primary_email
    customer = ingest_stripe_customer(dbsession, data)
    dbsession.commit()
    dbsession.refresh(customer)
    assert customer.stripe_id == FAKE_CUSTOMER_ID
    assert not customer.deleted
    assert customer.default_source_id is None
    assert customer.invoice_settings_default_payment_method_id == FAKE_PAYMENT_METHOD_ID
    assert customer.email_id == example_contact.email.email_id


def test_ingest_new_contact(dbsession):
    """A Stripe Customer creates a new contact if needed."""
    data = stripe_customer_data()
    customer = ingest_stripe_customer(dbsession, data)
    dbsession.commit()
    dbsession.refresh(customer)
    email_id = customer.email.email_id
    contact = get_contact_by_email_id(dbsession, email_id)
    assert contact["fxa"].fxa_id == data["description"]
    assert contact["fxa"].primary_email == data["email"]
    assert contact["email"].primary_email == data["email"]


def test_ingest_new_but_deleted_customer(dbsession):
    """A deleted Stripe Customer does not create a new contact."""
    data = {
        "deleted": True,
        "id": FAKE_CUSTOMER_ID,
        "object": "customer",
    }
    customer = ingest_stripe_customer(dbsession, data)
    assert customer is None


def test_ingest_new_fxa_user(dbsession):
    """A Stripe Customer creates a new FxA association if needed."""
    data = stripe_customer_data()
    fxa_id = data["description"]
    fxa_email = data["email"]
    email_id = str(uuid4())
    new_email = EmailInSchema(email_id=email_id, primary_email=fxa_email)
    create_email(dbsession, new_email)
    dbsession.commit()

    customer = ingest_stripe_customer(dbsession, data)
    dbsession.commit()
    dbsession.refresh(customer)
    email_id = customer.email.email_id
    contact = get_contact_by_email_id(dbsession, email_id)
    assert contact["fxa"].fxa_id == fxa_id
    assert contact["fxa"].primary_email == fxa_email
    assert contact["email"].primary_email == fxa_email


def test_ingest_update_customer(dbsession, stripe_customer):
    """A Stripe Customer can be updated."""
    data = stripe_customer_data()
    # Change payment method
    new_source_id = fake_stripe_id("card", "new credit card")
    data["default_source"] = new_source_id
    data["invoice_settings"]["default_payment_method"] = None

    customer = ingest_stripe_customer(dbsession, data)
    dbsession.commit()
    dbsession.refresh(customer)
    assert customer.default_source_id == new_source_id
    assert customer.invoice_settings_default_payment_method_id is None


def test_ingest_existing_but_deleted_customer(dbsession, stripe_customer):
    """A deleted Stripe Customer is noted for later deletion."""
    assert not stripe_customer.deleted

    data = {
        "deleted": True,
        "id": stripe_customer.stripe_id,
        "object": "customer",
    }
    customer = ingest_stripe_customer(dbsession, data)
    dbsession.commit()
    dbsession.refresh(customer)
    assert customer.deleted
    assert customer.default_source_id == stripe_customer.default_source_id
    assert (
        customer.invoice_settings_default_payment_method_id
        == stripe_customer.invoice_settings_default_payment_method_id
    )


def test_ingest_new_subscription(dbsession):
    """A new Stripe Subscription is ingested."""
    data = stripe_subscription_data()
    subscription = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()
    dbsession.refresh(subscription)
    assert subscription.stripe_id == FAKE_SUBSCRIPTION_ID
    assert subscription.stripe_created == datetime(2021, 9, 27, tzinfo=timezone.utc)
    assert subscription.stripe_customer_id == FAKE_CUSTOMER_ID
    assert not subscription.cancel_at_period_end
    assert subscription.canceled_at is None
    assert subscription.current_period_end == datetime(
        2021, 11, 27, tzinfo=timezone.utc
    )
    assert subscription.current_period_start == datetime(
        2021, 10, 27, tzinfo=timezone.utc
    )
    assert subscription.ended_at is None
    assert subscription.start_date == datetime(2021, 9, 27, tzinfo=timezone.utc)
    assert subscription.status == "active"
    assert subscription.default_payment_method_id is None

    # Can be created without the Customer object
    assert subscription.customer is None

    assert len(subscription.subscription_items) == 1
    item = subscription.subscription_items[0]
    assert item.stripe_id == FAKE_SUBSCRIPTION_ITEM_ID
    assert item.subscription == subscription

    price = item.price
    assert price.stripe_id == FAKE_PRICE_ID
    assert price.stripe_created == datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc)
    assert price.stripe_product_id == FAKE_PRODUCT_ID
    assert price.active
    assert price.currency == "usd"
    assert price.recurring_interval == "month"
    assert price.recurring_interval_count == 1
    assert price.unit_amount == 999


def test_ingest_update_subscription(dbsession, stripe_subscription):
    """An existing subscription is updated."""
    data = stripe_subscription_data()
    # Change to yearly
    current_period_end = stripe_subscription.current_period_end + timedelta(days=365)
    si_created = stripe_subscription.current_period_start + timedelta(days=15)
    data["current_period_end"] = unix_timestamp(current_period_end)
    data["items"]["data"][0] = {
        "id": fake_stripe_id("si", "new subscription id"),
        "object": "subscription_item",
        "created": unix_timestamp(current_period_end),
        "subscription": data["id"],
        "price": {
            "id": fake_stripe_id("price", "yearly price"),
            "object": "price",
            "created": unix_timestamp(si_created),
            "product": FAKE_PRODUCT_ID,
            "active": True,
            "currency": "usd",
            "recurring": {
                "interval": "year",
                "interval_count": 1,
            },
            "unit_amount": 4999,
        },
    }
    data["default_payment_method"] = fake_stripe_id("pm", "my new credit card")

    subscription = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()
    dbsession.refresh(subscription)
    assert subscription.current_period_end == current_period_end
    assert subscription.default_payment_method_id == data["default_payment_method"]

    assert len(subscription.subscription_items) == 1
    s_item = subscription.subscription_items[0]
    si_data = data["items"]["data"][0]
    assert s_item.stripe_id == si_data["id"]
    assert s_item.price.stripe_id == si_data["price"]["id"]


def test_ingest_cancelled_subscription(dbsession, stripe_subscription):
    """A subscription can move to canceled."""
    assert stripe_subscription.status == "active"
    data = stripe_subscription_data()
    data["cancel_at_period_end"] = True
    data["canceled_at"] = unix_timestamp(datetime(2021, 10, 29))
    data["current_period_end"] = unix_timestamp(datetime(2021, 11, 15))
    data["current_period_start"] = unix_timestamp(datetime(2021, 10, 15))
    data["ended_at"] = unix_timestamp(datetime(2021, 10, 29))
    data["start_date"] = unix_timestamp(datetime(2021, 9, 15))
    data["status"] = "canceled"
    subscription = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()
    assert subscription.stripe_id == stripe_subscription.stripe_id
    assert subscription.status == "canceled"


def test_ingest_update_price_via_subscription(dbsession, stripe_subscription):
    """A price object can be updated via a subscription update."""
    assert stripe_subscription.subscription_items[0].price.active

    data = stripe_subscription_data()
    data["items"]["data"][0]["price"]["active"] = False
    subscription = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()
    dbsession.refresh(subscription)

    assert len(subscription.subscription_items) == 1
    s_item = subscription.subscription_items[0]
    assert not s_item.price.active


def test_ingest_update_subscription_item(dbsession, stripe_subscription):
    """A subscription item can be updated."""
    data = stripe_subscription_data()
    new_price_id = fake_stripe_id("price", "monthly special")
    data["items"]["data"][0]["price"] = {
        "id": fake_stripe_id("price", "monthly special"),
        "object": "price",
        "created": unix_timestamp(datetime(2021, 10, 27, tzinfo=timezone.utc)),
        "product": FAKE_PRODUCT_ID,
        "active": True,
        "currency": "usd",
        "recurring": {
            "interval": "month",
            "interval_count": 1,
        },
        "unit_amount": 499,
    }
    subscription = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()
    dbsession.refresh(subscription)

    assert len(subscription.subscription_items) == 1
    s_item = subscription.subscription_items[0]
    assert s_item.price.stripe_id == new_price_id


def test_ingest_non_recurring_price(dbsession):
    """A non-recurring price with no unit_amount can be ingested."""
    data = {
        "id": fake_stripe_id("price", "non-recurring"),
        "object": "price",
        "created": unix_timestamp(),
        "product": FAKE_PRODUCT_ID,
        "active": True,
        "type": "one_time",
        "currency": "usd",
    }
    price = ingest_stripe_price(dbsession, data)
    assert price.recurring_interval is None
    assert price.recurring_interval_count is None
    assert price.unit_amount is None


@pytest.mark.parametrize("filename", ("customer_01.json", "subscription_01.json"))
def test_ingest_sample_data(dbsession, filename):
    """Stripe sample data can be ingested."""
    my_folder = os.path.dirname(__file__)
    test_folder = os.path.dirname(my_folder)
    stripe_data_folder = os.path.join(test_folder, "data", "stripe")
    sample_filepath = os.path.join(stripe_data_folder, filename)
    with open(sample_filepath, "r") as the_file:
        data = json.load(the_file)
    obj = ingest_stripe_object(dbsession, data)
    assert obj is not None


def test_ingest_unknown_stripe_object_raises(dbsession):
    """Ingesting an unknown type of Stripe object raises an exception."""
    data = {
        "id": fake_stripe_id("re", "refund"),
        "object": "refund",
    }
    with pytest.raises(StripeIngestUnknownObjectError) as excinfo:
        ingest_stripe_object(dbsession, data)
    exception = excinfo.value
    assert str(exception) == "Unknown Stripe object 'refund'."
    assert repr(exception) == "StripeIngestUnknownObjectError('refund')"


@pytest.mark.parametrize(
    "value", ("a string", {"value": "dict"}, ["list"]), ids=("string", "dict", "list")
)
def test_ingest_unknown_type_raises(dbsession, value):
    """Ingesting an unknown value raises an exception."""
    with pytest.raises(StripeIngestBadObjectError) as excinfo:
        ingest_stripe_object(dbsession, value)
    exception = excinfo.value
    assert str(exception) == "Data is not a Stripe object."
    assert repr(exception) == f"StripeIngestBadObjectError({value!r})"
