"""Test ingesting of Stripe data"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import mktime
from typing import Dict, Optional
from uuid import UUID

import pytest

from ctms.crud import (
    create_stripe_customer,
    create_stripe_invoice,
    create_stripe_invoice_line_item,
    create_stripe_price,
    create_stripe_subscription,
    create_stripe_subscription_item,
    get_stripe_customer_by_stripe_id,
    get_stripe_invoice_by_stripe_id,
    get_stripe_invoice_line_item_by_stripe_id,
    get_stripe_price_by_stripe_id,
    get_stripe_subscription_by_stripe_id,
    get_stripe_subscription_item_by_stripe_id,
)
from ctms.ingest_stripe import (
    StripeIngestBadObjectError,
    StripeIngestUnknownObjectError,
    ingest_stripe_customer,
    ingest_stripe_invoice,
    ingest_stripe_object,
    ingest_stripe_price,
    ingest_stripe_subscription,
)
from ctms.schemas import (
    StripeCustomerCreateSchema,
    StripeInvoiceCreateSchema,
    StripeInvoiceLineItemCreateSchema,
    StripePriceCreateSchema,
    StripeSubscriptionCreateSchema,
    StripeSubscriptionItemCreateSchema,
)
from tests.unit.sample_data import FAKE_STRIPE_ID, SAMPLE_STRIPE_DATA, fake_stripe_id
from tests.unit.test_crud import StatementWatcher


def unix_timestamp(the_time: Optional[datetime] = None) -> int:
    """Create a UNIX timestamp from a datetime or now"""
    the_time = the_time or datetime.now(tz=timezone.utc)
    return int(mktime(the_time.timetuple()))


def stripe_customer_data() -> Dict:
    """Return minimal Stripe customer data."""
    sample = SAMPLE_STRIPE_DATA["Customer"]
    return {
        "id": sample["stripe_id"],
        "object": "customer",
        "created": unix_timestamp(sample["stripe_created"]),
        "description": sample["fxa_id"],
        "email": "fxa_email@example.com",
        "default_source": sample["default_source_id"],
        "invoice_settings": {
            "default_payment_method": sample[
                "invoice_settings_default_payment_method_id"
            ],
        },
    }


@pytest.fixture
def stripe_customer(dbsession, example_contact):
    """Return a Stripe Customer associated with the example contact."""
    data = SAMPLE_STRIPE_DATA["Customer"]
    schema = StripeCustomerCreateSchema(**data)
    customer = create_stripe_customer(dbsession, schema)
    dbsession.commit()
    dbsession.refresh(customer)
    return customer


def stripe_subscription_data() -> Dict:
    """Return minimal Stripe subscription data."""
    data = SAMPLE_STRIPE_DATA["Subscription"]
    item_data = SAMPLE_STRIPE_DATA["SubscriptionItem"]
    return {
        "id": data["stripe_id"],
        "object": "subscription",
        "created": unix_timestamp(data["stripe_created"]),
        "customer": data["stripe_customer_id"],
        "cancel_at_period_end": data["cancel_at_period_end"],
        "canceled_at": data["canceled_at"],
        "current_period_start": unix_timestamp(data["current_period_start"]),
        "current_period_end": unix_timestamp(data["current_period_end"]),
        "ended_at": data["ended_at"],
        "start_date": unix_timestamp(data["start_date"]),
        "status": data["status"],
        "default_source": data["default_source_id"],
        "default_payment_method": data["default_payment_method_id"],
        "items": {
            "object": "list",
            "total_count": 1,
            "has_more": False,
            "url": f"/v1/subscription_items?subscription={data['stripe_id']}",
            "data": [
                {
                    "id": item_data["stripe_id"],
                    "object": "subscription_item",
                    "created": unix_timestamp(item_data["stripe_created"]),
                    "subscription": item_data["stripe_subscription_id"],
                    "price": stripe_price_data(),
                }
            ],
        },
    }


@pytest.fixture
def stripe_subscription(dbsession, stripe_price):
    data = SAMPLE_STRIPE_DATA["Subscription"]
    subscription = StripeSubscriptionCreateSchema(**data)
    db_subscription = create_stripe_subscription(dbsession, subscription)
    item_data = SAMPLE_STRIPE_DATA["SubscriptionItem"]
    subscription_item = StripeSubscriptionItemCreateSchema(**item_data)
    db_subscription_item = create_stripe_subscription_item(dbsession, subscription_item)
    assert db_subscription_item

    dbsession.commit()
    dbsession.refresh(db_subscription)
    return db_subscription


def stripe_price_data() -> Dict:
    """Return minimal Stripe price data."""
    data = SAMPLE_STRIPE_DATA["Price"]
    return {
        "id": data["stripe_id"],
        "object": "price",
        "created": unix_timestamp(data["stripe_created"]),
        "product": data["stripe_product_id"],
        "active": data["active"],
        "currency": data["currency"],
        "recurring": {
            "interval": data["recurring_interval"],
            "interval_count": data["recurring_interval_count"],
        },
        "unit_amount": data["unit_amount"],
    }


@pytest.fixture
def stripe_price(dbsession):
    data = SAMPLE_STRIPE_DATA["Price"]
    price = StripePriceCreateSchema(**data)
    db_price = create_stripe_price(dbsession, price)
    assert db_price
    dbsession.commit()
    dbsession.refresh(db_price)
    return db_price


def stripe_invoice_data() -> Dict:
    """Return minimal Stripe invoice data."""
    data = SAMPLE_STRIPE_DATA["Invoice"]
    item_data = SAMPLE_STRIPE_DATA["InvoiceLineItem"]
    return {
        "id": data["stripe_id"],
        "object": "invoice",
        "created": unix_timestamp(data["stripe_created"]),
        "customer": data["stripe_customer_id"],
        "currency": data["currency"],
        "total": data["total"],
        "default_source": data["default_source_id"],
        "default_payment_method": data["default_payment_method_id"],
        "status": data["status"],
        "lines": {
            "object": "list",
            "total_count": 1,
            "has_more": False,
            "url": f"/v1/invoices/{data['stripe_id']}/lines",
            "data": [
                {
                    "id": item_data["stripe_id"],
                    "object": "line_item",
                    "type": item_data["stripe_type"],
                    "subscription": item_data["stripe_subscription_id"],
                    "subscription_item": item_data["stripe_subscription_item_id"],
                    "price": stripe_price_data(),
                    "amount": item_data["amount"],
                    "currency": item_data["currency"],
                }
            ],
        },
    }


@pytest.fixture
def stripe_invoice(dbsession, stripe_customer, stripe_price):
    data = SAMPLE_STRIPE_DATA["Invoice"]
    invoice = StripeInvoiceCreateSchema(**data)
    db_invoice = create_stripe_invoice(dbsession, invoice)
    assert db_invoice

    item_data = SAMPLE_STRIPE_DATA["InvoiceLineItem"]
    invoice_item = StripeInvoiceLineItemCreateSchema(**item_data)
    db_invoice_item = create_stripe_invoice_line_item(dbsession, invoice_item)
    assert db_invoice_item
    dbsession.commit()
    dbsession.refresh(db_invoice)
    return db_invoice


def test_ids():
    """Get the fake IDs, to make it easier to copy to schemas."""
    assert FAKE_STRIPE_ID["Customer"] == "cus_Y3VzdG9tZXI"
    assert FAKE_STRIPE_ID["Invoice"] == "in_aW52b2ljZQ"
    assert FAKE_STRIPE_ID["(Invoice) Line Item"] == "il_aW52b2ljZSBsaW5lIGl0ZW0"
    assert FAKE_STRIPE_ID["Payment Method"] == "pm_cGF5bWVudF9tZXRob2Q"
    assert FAKE_STRIPE_ID["Price"] == "price_cHJpY2U"
    assert FAKE_STRIPE_ID["Product"] == "prod_cHJvZHVjdA"
    assert FAKE_STRIPE_ID["Subscription"] == "sub_c3Vic2NyaXB0aW9u"
    assert FAKE_STRIPE_ID["Subscription Item"] == "si_c3Vic2NyaXB0aW9uX2l0ZW0"


def test_ingest_existing_contact(dbsession, example_contact):
    """A Stripe Customer is associated with the existing contact."""
    data = stripe_customer_data()
    data["description"] = example_contact.fxa.fxa_id
    data["email"] = example_contact.fxa.primary_email

    with StatementWatcher(dbsession.connection()) as watcher:
        customer = ingest_stripe_customer(dbsession, data)
        dbsession.commit()
    assert watcher.count == 2
    stmt1 = watcher.statements[0][0]
    assert stmt1.startswith("SELECT stripe_customer."), stmt1
    assert stmt1.endswith(" FOR UPDATE"), stmt1
    stmt2 = watcher.statements[1][0]
    assert stmt2.startswith("INSERT INTO stripe_customer "), stmt2

    assert customer.stripe_id == FAKE_STRIPE_ID["Customer"]
    assert not customer.deleted
    assert customer.default_source_id is None
    assert (
        customer.invoice_settings_default_payment_method_id
        == FAKE_STRIPE_ID["Payment Method"]
    )
    assert customer.fxa_id == example_contact.fxa.fxa_id
    assert customer.get_email_id() == example_contact.email.email_id


def test_ingest_without_contact(dbsession):
    """A Stripe Customer can be ingested without a contact."""
    data = stripe_customer_data()
    customer = ingest_stripe_customer(dbsession, data)
    dbsession.commit()
    dbsession.refresh(customer)
    assert customer.email is None


def test_ingest_deleted_customer(dbsession):
    """A deleted Stripe Customer is not ingested."""
    data = {
        "deleted": True,
        "id": FAKE_STRIPE_ID["Customer"],
        "object": "customer",
    }
    customer = ingest_stripe_customer(dbsession, data)
    assert customer is None


def test_ingest_update_customer(dbsession, stripe_customer):
    """A Stripe Customer can be updated."""
    data = stripe_customer_data()
    # Change payment method
    new_source_id = fake_stripe_id("card", "new credit card")
    data["default_source"] = new_source_id
    data["invoice_settings"]["default_payment_method"] = None

    with StatementWatcher(dbsession.connection()) as watcher:
        customer = ingest_stripe_customer(dbsession, data)
        dbsession.commit()
    assert watcher.count == 2
    stmt1 = watcher.statements[0][0]
    assert stmt1.startswith("SELECT stripe_customer."), stmt1
    assert stmt1.endswith(" FOR UPDATE"), stmt1
    stmt2 = watcher.statements[1][0]
    assert stmt2.startswith("UPDATE stripe_customer SET "), stmt2

    assert customer.default_source_id == new_source_id
    assert customer.invoice_settings_default_payment_method_id is None


def test_ingest_existing_but_deleted_customer(
    dbsession, stripe_customer, example_contact
):
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
    assert customer.get_email_id() == example_contact.email.email_id


def test_ingest_new_subscription(dbsession):
    """A new Stripe Subscription is ingested."""
    data = stripe_subscription_data()

    with StatementWatcher(dbsession.connection()) as watcher:
        subscription = ingest_stripe_subscription(dbsession, data)
        dbsession.commit()
    assert watcher.count == 6
    stmt1, stmt2, stmt3, stmt4, stmt5, stmt6 = [pair[0] for pair in watcher.statements]
    assert stmt1.startswith("SELECT stripe_subscription."), stmt1
    assert stmt1.endswith(" FOR UPDATE"), stmt1
    assert stmt2.startswith("SELECT stripe_price."), stmt2
    assert stmt2.endswith(" FOR UPDATE"), stmt2
    assert stmt3.startswith("SELECT stripe_subscription_item."), stmt3
    assert stmt3.endswith(" FOR UPDATE"), stmt3
    # Insert order could be swapped
    assert stmt4.startswith("INSERT INTO stripe_"), stmt4
    assert stmt5.startswith("INSERT INTO stripe_"), stmt5
    assert stmt6.startswith("INSERT INTO stripe_"), stmt6

    assert subscription.stripe_id == FAKE_STRIPE_ID["Subscription"]
    assert subscription.stripe_created == datetime(2021, 9, 27, tzinfo=timezone.utc)
    assert subscription.stripe_customer_id == FAKE_STRIPE_ID["Customer"]
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
    assert subscription.get_email_id() is None

    # Can be created without the Customer object
    assert subscription.customer is None

    assert len(subscription.subscription_items) == 1
    item = subscription.subscription_items[0]
    assert item.stripe_id == FAKE_STRIPE_ID["Subscription Item"]
    assert item.subscription == subscription
    assert item.get_email_id() is None

    price = item.price
    assert price.stripe_id == FAKE_STRIPE_ID["Price"]
    assert price.stripe_created == datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc)
    assert price.stripe_product_id == FAKE_STRIPE_ID["Product"]
    assert price.active
    assert price.currency == "usd"
    assert price.recurring_interval == "month"
    assert price.recurring_interval_count == 1
    assert price.unit_amount == 999
    assert price.get_email_id() is None


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
            "product": FAKE_STRIPE_ID["Product"],
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

    with StatementWatcher(dbsession.connection()) as watcher:
        subscription = ingest_stripe_subscription(dbsession, data)
        dbsession.commit()
    assert watcher.count == 8
    stmt1, stmt2, stmt3, stmt4, stmt5, stmt6, stmt7, stmt8 = [
        pair[0] for pair in watcher.statements
    ]
    assert stmt1.startswith("SELECT stripe_subscription."), stmt1
    assert stmt1.endswith(" FOR UPDATE"), stmt1
    # Get all IDs
    assert stmt2.startswith("SELECT stripe_subscription_item.stripe_id "), stmt2
    assert stmt2.endswith(" FOR UPDATE"), stmt2
    # Load item 1
    # Can't eager load items with FOR UPDATE, need to query twice
    assert stmt3.startswith("SELECT stripe_price."), stmt3
    assert stmt3.endswith(" FOR UPDATE"), stmt3
    assert stmt4.startswith("SELECT stripe_subscription_item."), stmt4
    assert stmt4.endswith(" FOR UPDATE"), stmt4
    # Delete old item
    assert stmt5.startswith("DELETE FROM stripe_subscription_item "), stmt5
    # Insert order could be swapped
    insert = "INSERT INTO stripe_"
    update = "UPDATE stripe_subscription SET "
    assert stmt6.startswith(insert) or stmt6.startswith(update), stmt6
    assert stmt7.startswith(insert) or stmt7.startswith(update), stmt7
    assert stmt8.startswith(insert) or stmt8.startswith(update), stmt8

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
        "product": FAKE_STRIPE_ID["Product"],
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
        "product": FAKE_STRIPE_ID["Product"],
        "active": True,
        "type": "one_time",
        "currency": "usd",
    }
    price = ingest_stripe_price(dbsession, data)
    assert price.recurring_interval is None
    assert price.recurring_interval_count is None
    assert price.unit_amount is None
    assert price.get_email_id() is None


def test_ingest_new_invoice(dbsession):
    """A new Stripe Invoice is ingested."""
    data = stripe_invoice_data()

    with StatementWatcher(dbsession.connection()) as watcher:
        invoice = ingest_stripe_invoice(dbsession, data)
        dbsession.commit()
    assert watcher.count == 6
    stmt1, stmt2, stmt3, stmt4, stmt5, stmt6 = [pair[0] for pair in watcher.statements]
    assert stmt1.startswith("SELECT stripe_invoice."), stmt1
    assert stmt1.endswith(" FOR UPDATE"), stmt1
    assert stmt2.startswith("SELECT stripe_price."), stmt2
    assert stmt2.endswith(" FOR UPDATE"), stmt2
    assert stmt3.startswith("SELECT stripe_invoice_line_item."), stmt3
    assert stmt3.endswith(" FOR UPDATE"), stmt3
    # Insert order could be swapped
    assert stmt4.startswith("INSERT INTO stripe_"), stmt4
    assert stmt5.startswith("INSERT INTO stripe_"), stmt5
    assert stmt6.startswith("INSERT INTO stripe_"), stmt6

    assert invoice.stripe_id == FAKE_STRIPE_ID["Invoice"]
    assert invoice.stripe_created == datetime(2021, 10, 28, tzinfo=timezone.utc)
    assert invoice.stripe_customer_id == FAKE_STRIPE_ID["Customer"]
    assert invoice.currency == "usd"
    assert invoice.total == 1000
    assert invoice.status == "open"
    assert invoice.default_payment_method_id is None
    assert invoice.default_source_id is None
    assert invoice.get_email_id() is None

    # Can be created without the Customer object
    assert invoice.customer is None

    assert len(invoice.line_items) == 1
    item = invoice.line_items[0]
    assert item.stripe_id == FAKE_STRIPE_ID["(Invoice) Line Item"]
    assert item.invoice == invoice
    assert item.stripe_subscription_id == FAKE_STRIPE_ID["Subscription"]
    assert item.stripe_subscription_item_id == FAKE_STRIPE_ID["Subscription Item"]
    assert item.stripe_invoice_item_id is None
    assert item.amount == 1000
    assert item.currency == "usd"
    assert item.get_email_id() is None

    price = item.price
    assert price.stripe_id == FAKE_STRIPE_ID["Price"]
    assert price.stripe_created == datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc)
    assert price.stripe_product_id == FAKE_STRIPE_ID["Product"]
    assert price.active
    assert price.currency == "usd"
    assert price.recurring_interval == "month"
    assert price.recurring_interval_count == 1
    assert price.unit_amount == 999
    assert price.get_email_id() is None


def test_ingest_updated_invoice(dbsession, stripe_invoice):
    """An existing Stripe Invoice is updated."""
    assert stripe_invoice.status == "open"
    data = stripe_invoice_data()
    data["status"] = "void"
    with StatementWatcher(dbsession.connection()) as watcher:
        invoice = ingest_stripe_invoice(dbsession, data)
        dbsession.commit()
    assert watcher.count == 6
    stmt1, stmt2, stmt3, stmt4, stmt5, stmt6 = [pair[0] for pair in watcher.statements]
    assert stmt1.startswith("SELECT stripe_invoice."), stmt1
    assert stmt1.endswith(" FOR UPDATE"), stmt1
    # Get all IDs
    assert stmt2.startswith("SELECT stripe_invoice_line_item.stripe_id "), stmt2
    assert stmt2.endswith(" FOR UPDATE"), stmt2
    # Load line item 1
    # Can't eager load items with FOR UPDATE, need to query twice
    assert stmt3.startswith("SELECT stripe_price."), stmt3
    assert stmt3.endswith(" FOR UPDATE"), stmt3
    assert stmt4.startswith("SELECT stripe_invoice_line_item."), stmt4
    assert stmt4.endswith(" FOR UPDATE"), stmt4
    # Updates price, invoice, in unknown order
    assert stmt5.startswith("UPDATE stripe_"), stmt5
    assert stmt6.startswith("UPDATE stripe_"), stmt6

    assert invoice.status == "void"
    assert len(invoice.line_items) == 1


def test_ingest_updated_invoice_lines(dbsession, stripe_invoice):
    """The Stripe Invoice lines are synced on update."""
    data = stripe_invoice_data()
    new_line_item_id = fake_stripe_id("il", "new line item")
    data["lines"]["data"][0] = {
        "id": new_line_item_id,
        "object": "line_item",
        "type": "subscription",
        "created": unix_timestamp(datetime(2021, 10, 28, tzinfo=timezone.utc)),
        "subscription": FAKE_STRIPE_ID["Subscription"],
        "subscription_item": FAKE_STRIPE_ID["Subscription Item"],
        "price": stripe_price_data(),
        "amount": 500,
        "currency": "usd",
    }
    invoice = ingest_stripe_invoice(dbsession, data)
    dbsession.commit()
    assert len(invoice.line_items) == 1
    assert invoice.line_items[0].stripe_id == new_line_item_id


def test_ingest_sample_data(dbsession, stripe_test_json):
    """Stripe sample JSON can be ingested."""
    obj = ingest_stripe_object(dbsession, stripe_test_json)
    assert obj is not None
    assert type(obj.get_email_id()) in (type(None), UUID)


def test_get_email_id_customer(dbsession, contact_with_stripe_customer):
    """A Stripe Customer can return the related email_id."""
    customer = get_stripe_customer_by_stripe_id(dbsession, FAKE_STRIPE_ID["Customer"])
    assert customer.get_email_id() == contact_with_stripe_customer.email.email_id


def test_get_email_id_subscription(dbsession, contact_with_stripe_subscription):
    """A Stripe Subscription and related objects can return the related email_id."""
    customer = get_stripe_customer_by_stripe_id(dbsession, FAKE_STRIPE_ID["Customer"])
    subscription = get_stripe_subscription_by_stripe_id(
        dbsession, FAKE_STRIPE_ID["Subscription"]
    )
    subscription_item = get_stripe_subscription_item_by_stripe_id(
        dbsession, FAKE_STRIPE_ID["Subscription Item"]
    )
    price = get_stripe_price_by_stripe_id(dbsession, FAKE_STRIPE_ID["Price"])

    email_id = contact_with_stripe_subscription.email.email_id
    assert customer.get_email_id() == email_id
    assert subscription.get_email_id() == email_id
    assert subscription_item.get_email_id() == email_id
    # Prices always return None since they can relate to multiple contacts.
    assert price.get_email_id() is None


def test_get_email_id_invoice(dbsession, contact_with_stripe_customer):
    """A Stripe Invoice and related objects can return the related email_id."""
    invoice = ingest_stripe_invoice(dbsession, stripe_invoice_data())
    dbsession.commit()
    customer = get_stripe_customer_by_stripe_id(dbsession, FAKE_STRIPE_ID["Customer"])
    invoice = get_stripe_invoice_by_stripe_id(dbsession, FAKE_STRIPE_ID["Invoice"])
    line_item = get_stripe_invoice_line_item_by_stripe_id(
        dbsession, FAKE_STRIPE_ID["(Invoice) Line Item"]
    )
    price = get_stripe_price_by_stripe_id(dbsession, FAKE_STRIPE_ID["Price"])

    email_id = contact_with_stripe_customer.email.email_id
    assert customer.get_email_id() == email_id
    assert invoice.get_email_id() == email_id
    assert line_item.get_email_id() == email_id
    # Prices always return None since they can relate to multiple contacts.
    assert price.get_email_id() is None


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
