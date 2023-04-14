"""Test ingesting of Stripe data"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

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
    StripeIngestFxAIdConflict,
    StripeIngestUnknownObjectError,
    StripeToAcousticParseError,
    add_stripe_object_to_acoustic_queue,
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
from tests.data import fake_stripe_id
from tests.unit.conftest import unix_timestamp


@pytest.fixture
def stripe_customer(dbsession, example_contact, stripe_customer_data):
    """Return a Stripe Customer associated with the example contact."""
    schema = StripeCustomerCreateSchema(**stripe_customer_data)
    customer = create_stripe_customer(dbsession, schema)
    dbsession.commit()
    dbsession.refresh(customer)
    return customer


@pytest.fixture
def stripe_price(dbsession, stripe_price_data):
    price = StripePriceCreateSchema(**stripe_price_data)
    db_price = create_stripe_price(dbsession, price)
    assert db_price
    dbsession.commit()
    dbsession.refresh(db_price)
    return db_price


@pytest.fixture
def stripe_subscription(
    dbsession, stripe_price, stripe_subscription_data, stripe_subscription_item_data
):
    subscription = StripeSubscriptionCreateSchema(**stripe_subscription_data)
    db_subscription = create_stripe_subscription(dbsession, subscription)
    subscription_item = StripeSubscriptionItemCreateSchema(
        **stripe_subscription_item_data
    )
    db_subscription_item = create_stripe_subscription_item(dbsession, subscription_item)
    assert db_subscription_item

    dbsession.commit()
    dbsession.refresh(db_subscription)
    return db_subscription


@pytest.fixture
def stripe_invoice(
    dbsession,
    stripe_customer,
    stripe_price,
    stripe_invoice_data,
    stripe_invoice_line_item_data,
):
    invoice = StripeInvoiceCreateSchema(**stripe_invoice_data)
    db_invoice = create_stripe_invoice(dbsession, invoice)
    assert db_invoice

    invoice_item = StripeInvoiceLineItemCreateSchema(**stripe_invoice_line_item_data)
    db_invoice_item = create_stripe_invoice_line_item(dbsession, invoice_item)
    assert db_invoice_item
    dbsession.commit()
    dbsession.refresh(db_invoice)
    return db_invoice


def test_ingest_existing_contact(dbsession, example_contact, raw_stripe_customer_data):
    """A Stripe Customer is associated with the existing contact."""
    data = raw_stripe_customer_data
    data["description"] = example_contact.fxa.fxa_id
    data["email"] = example_contact.fxa.primary_email

    customer, actions = ingest_stripe_customer(dbsession, data)
    dbsession.commit()

    assert customer.stripe_id == raw_stripe_customer_data["id"]
    assert not customer.deleted
    assert customer.default_source_id is None
    assert (
        customer.invoice_settings_default_payment_method_id
        == raw_stripe_customer_data["invoice_settings"]["default_payment_method"]
    )
    assert customer.fxa_id == example_contact.fxa.fxa_id
    assert customer.get_email_id() == example_contact.email.email_id
    assert actions == {
        "created": {
            f"customer:{customer.stripe_id}",
        }
    }


def test_ingest_without_contact(dbsession, raw_stripe_customer_data):
    """A Stripe Customer can be ingested without a contact."""
    data = raw_stripe_customer_data
    customer, actions = ingest_stripe_customer(dbsession, data)
    dbsession.commit()
    dbsession.refresh(customer)
    assert customer.email is None
    assert actions == {
        "created": {
            f"customer:{data['id']}",
        }
    }


def test_ingest_deleted_customer(dbsession):
    """A deleted Stripe Customer is not ingested."""
    data = {
        "deleted": True,
        "id": fake_stripe_id("cus", "deleted_customer"),
        "object": "customer",
    }
    customer, actions = ingest_stripe_customer(dbsession, data)
    assert customer is None
    assert actions == {
        "skipped": {
            f"customer:{data['id']}",
        }
    }


def test_ingest_update_customer(dbsession, stripe_customer, raw_stripe_customer_data):
    """A Stripe Customer can be updated."""
    data = raw_stripe_customer_data
    # Change payment method
    new_source_id = fake_stripe_id("card", "new credit card")
    data["default_source"] = new_source_id
    data["invoice_settings"]["default_payment_method"] = None

    customer, actions = ingest_stripe_customer(dbsession, data)
    dbsession.commit()

    assert customer.default_source_id == new_source_id
    assert customer.invoice_settings_default_payment_method_id is None
    assert actions == {
        "updated": {
            f"customer:{data['id']}",
        }
    }


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
    customer, actions = ingest_stripe_customer(dbsession, data)
    dbsession.commit()
    dbsession.refresh(customer)
    assert customer.deleted
    assert customer.default_source_id == stripe_customer.default_source_id
    assert (
        customer.invoice_settings_default_payment_method_id
        == stripe_customer.invoice_settings_default_payment_method_id
    )
    assert customer.get_email_id() == example_contact.email.email_id
    assert actions == {
        "updated": {
            f"customer:{data['id']}",
        }
    }


def test_ingest_new_customer_duplicate_fxa_id(
    dbsession, stripe_customer, example_contact, raw_stripe_customer_data
):
    """StripeIngestFxAIdConflict is raised when an existing customer has the same FxA ID."""
    data = raw_stripe_customer_data
    existing_id = data["id"]
    fxa_id = data["description"]
    data["id"] = fake_stripe_id("cust", "duplicate_fxa_id")
    with pytest.raises(StripeIngestFxAIdConflict) as excinfo:
        ingest_stripe_customer(dbsession, data)
    exception = excinfo.value
    assert (
        str(exception)
        == f"Existing StripeCustomer '{existing_id}' has FxA ID '{fxa_id}'."
    )
    assert repr(exception) == f"StripeIngestFxAIdConflict('{existing_id}', '{fxa_id}')"


def test_ingest_update_customer_duplicate_fxa_id(
    dbsession, stripe_customer, stripe_customer_data, raw_stripe_customer_data
):
    """StripeIngestFxAIdConflict is raised when updating to a different customer's FxA ID."""
    existing_customer_data = stripe_customer_data
    existing_id = fake_stripe_id("cust", "duplicate_fxa_id")
    fxa_id = str(uuid4())
    existing_customer_data.update({"stripe_id": existing_id, "fxa_id": fxa_id})
    create_stripe_customer(
        dbsession, StripeCustomerCreateSchema(**existing_customer_data)
    )
    dbsession.commit()

    data = raw_stripe_customer_data
    data["description"] = fxa_id

    with pytest.raises(StripeIngestFxAIdConflict) as excinfo:
        ingest_stripe_customer(dbsession, data)

    exception = excinfo.value
    assert exception.stripe_id == existing_id
    assert exception.fxa_id == fxa_id


def test_ingest_new_subscription(dbsession, raw_stripe_subscription_data):
    """A new Stripe Subscription is ingested."""
    data = raw_stripe_subscription_data

    subscription, actions = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()

    assert subscription.stripe_id == raw_stripe_subscription_data["id"]
    assert subscription.stripe_created == datetime(2021, 9, 27, tzinfo=timezone.utc)
    assert subscription.stripe_customer_id == raw_stripe_subscription_data["customer"]
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
    assert item.stripe_id == raw_stripe_subscription_data["items"]["data"][0]["id"]
    assert item.subscription == subscription
    assert item.get_email_id() is None

    price = item.price
    assert (
        price.stripe_id
        == raw_stripe_subscription_data["items"]["data"][0]["price"]["id"]
    )
    assert price.stripe_created == datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc)
    assert price.stripe_product_id == data["items"]["data"][0]["price"]["product"]
    assert price.active
    assert price.currency == "usd"
    assert price.recurring_interval == "month"
    assert price.recurring_interval_count == 1
    assert price.unit_amount == 999
    assert price.get_email_id() is None

    assert actions == {
        "created": {
            f"subscription:{raw_stripe_subscription_data['id']}",
            f"subscription_item:{raw_stripe_subscription_data['items']['data'][0]['id']}",
            f"price:{raw_stripe_subscription_data['items']['data'][0]['price']['id']}",
        }
    }


def test_ingest_update_subscription(
    dbsession, stripe_subscription, raw_stripe_subscription_data
):
    """An existing subscription is updated."""
    data = raw_stripe_subscription_data
    # Change to yearly
    current_period_end = stripe_subscription.current_period_end + timedelta(days=365)
    si_created = stripe_subscription.current_period_start + timedelta(days=15)
    data["current_period_end"] = unix_timestamp(current_period_end)
    old_sub_item_id = data["items"]["data"][0]["id"]
    new_sub_item_id = fake_stripe_id("si", "new subscription item id")
    new_price_id = fake_stripe_id("price", "yearly price")
    data["items"]["data"][0] = {
        "id": new_sub_item_id,
        "object": "subscription_item",
        "created": unix_timestamp(current_period_end),
        "subscription": data["id"],
        "price": {
            "id": new_price_id,
            "object": "price",
            "created": unix_timestamp(si_created),
            "product": data["items"]["data"][0]["price"]["product"],
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

    subscription, actions = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()

    assert subscription.current_period_end == current_period_end
    assert subscription.default_payment_method_id == data["default_payment_method"]

    assert len(subscription.subscription_items) == 1
    s_item = subscription.subscription_items[0]
    assert s_item.stripe_id == new_sub_item_id
    assert s_item.price.stripe_id == new_price_id

    assert actions == {
        "created": {
            f"subscription_item:{new_sub_item_id}",
            f"price:{new_price_id}",
        },
        "updated": {
            f"subscription:{data['id']}",
        },
        "deleted": {
            f"subscription_item:{old_sub_item_id}",
        },
    }


def test_ingest_cancelled_subscription(
    dbsession, stripe_subscription, raw_stripe_subscription_data
):
    """A subscription can move to canceled."""
    assert stripe_subscription.status == "active"
    data = raw_stripe_subscription_data
    data["cancel_at_period_end"] = True
    data["canceled_at"] = unix_timestamp(datetime(2021, 10, 29))
    data["current_period_end"] = unix_timestamp(datetime(2021, 11, 15))
    data["current_period_start"] = unix_timestamp(datetime(2021, 10, 15))
    data["ended_at"] = unix_timestamp(datetime(2021, 10, 29))
    data["start_date"] = unix_timestamp(datetime(2021, 9, 15))
    data["status"] = "canceled"
    subscription, actions = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()
    assert subscription.stripe_id == stripe_subscription.stripe_id
    assert subscription.status == "canceled"
    assert actions == {
        "no_change": {
            f"price:{data['items']['data'][0]['price']['id']}",
            f"subscription_item:{data['items']['data'][0]['id']}",
        },
        "updated": {
            f"subscription:{data['id']}",
        },
    }


def test_ingest_update_price_via_subscription(
    dbsession, stripe_subscription, raw_stripe_subscription_data
):
    """A price object can be updated via a subscription update."""
    assert stripe_subscription.subscription_items[0].price.active

    data = raw_stripe_subscription_data
    data["items"]["data"][0]["price"]["active"] = False
    subscription, actions = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()
    dbsession.refresh(subscription)

    assert len(subscription.subscription_items) == 1
    s_item = subscription.subscription_items[0]
    assert not s_item.price.active
    assert actions == {
        "updated": {
            f"price:{data['items']['data'][0]['price']['id']}",
        },
        "no_change": {
            f"subscription:{data['id']}",
            f"subscription_item:{data['items']['data'][0]['id']}",
        },
    }


def test_ingest_update_subscription_item(
    dbsession, stripe_subscription, raw_stripe_subscription_data
):
    """A subscription item can be updated."""
    data = raw_stripe_subscription_data
    new_price_id = fake_stripe_id("price", "monthly special")
    data["items"]["data"][0]["price"] = {
        "id": fake_stripe_id("price", "monthly special"),
        "object": "price",
        "created": unix_timestamp(datetime(2021, 10, 27, tzinfo=timezone.utc)),
        "product": data["items"]["data"][0]["price"]["product"],
        "active": True,
        "currency": "usd",
        "recurring": {
            "interval": "month",
            "interval_count": 1,
        },
        "unit_amount": 499,
    }
    subscription, actions = ingest_stripe_subscription(dbsession, data)
    dbsession.commit()
    dbsession.refresh(subscription)

    assert len(subscription.subscription_items) == 1
    s_item = subscription.subscription_items[0]
    assert s_item.price.stripe_id == new_price_id
    assert actions == {
        "updated": {
            f"subscription_item:{data['items']['data'][0]['id']}",
        },
        "created": {
            f"price:{data['items']['data'][0]['price']['id']}",
        },
        "no_change": {
            f"subscription:{data['id']}",
        },
    }


def test_ingest_non_recurring_price(dbsession):
    """A non-recurring price with no unit_amount can be ingested."""
    data = {
        "id": fake_stripe_id("price", "non-recurring"),
        "object": "price",
        "created": unix_timestamp(),
        "product": fake_stripe_id("prod", "test_product"),
        "active": True,
        "type": "one_time",
        "currency": "usd",
    }
    price, actions = ingest_stripe_price(dbsession, data)
    assert price.recurring_interval is None
    assert price.recurring_interval_count is None
    assert price.unit_amount is None
    assert price.get_email_id() is None
    assert actions == {
        "created": {
            f"price:{data['id']}",
        }
    }


def test_ingest_new_invoice(dbsession, raw_stripe_invoice_data):
    """A new Stripe Invoice is ingested."""
    data = raw_stripe_invoice_data
    invoice, actions = ingest_stripe_invoice(dbsession, data)
    dbsession.commit()

    assert invoice.stripe_id == data["id"]
    assert invoice.stripe_created == datetime(2021, 10, 28, tzinfo=timezone.utc)
    assert invoice.stripe_customer_id == data["customer"]
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
    assert item.stripe_id == data["lines"]["data"][0]["id"]
    assert item.invoice == invoice
    assert item.stripe_subscription_id == data["lines"]["data"][0]["subscription"]
    assert (
        item.stripe_subscription_item_id
        == data["lines"]["data"][0]["subscription_item"]
    )
    assert item.stripe_invoice_item_id is None
    assert item.amount == 1000
    assert item.currency == "usd"
    assert item.get_email_id() is None

    price = item.price
    assert price.stripe_id == data["lines"]["data"][0]["price"]["id"]
    assert price.stripe_created == datetime(2020, 10, 27, 10, 45, tzinfo=timezone.utc)
    assert price.stripe_product_id == data["lines"]["data"][0]["price"]["product"]
    assert price.active
    assert price.currency == "usd"
    assert price.recurring_interval == "month"
    assert price.recurring_interval_count == 1
    assert price.unit_amount == 999
    assert price.get_email_id() is None

    assert actions == {
        "created": {
            f"invoice:{data['id']}",
            f"line_item:{item.stripe_id}",
            f"price:{price.stripe_id}",
        },
    }


def test_ingest_updated_invoice(dbsession, stripe_invoice, raw_stripe_invoice_data):
    """An existing Stripe Invoice is updated."""
    assert stripe_invoice.status == "open"
    data = raw_stripe_invoice_data
    data["status"] = "void"
    invoice, actions = ingest_stripe_invoice(dbsession, data)
    dbsession.commit()

    assert invoice.status == "void"
    assert len(invoice.line_items) == 1

    assert actions == {
        "updated": {
            f"invoice:{data['id']}",
        },
        "no_change": {
            f"line_item:{data['lines']['data'][0]['id']}",
            f"price:{data['lines']['data'][0]['price']['id']}",
        },
    }


def test_ingest_updated_invoice_lines(
    dbsession, stripe_invoice, raw_stripe_invoice_data, raw_stripe_price_data
):
    """The Stripe Invoice lines are synced on update."""
    data = raw_stripe_invoice_data
    old_line_item_id = data["lines"]["data"][0]["id"]
    new_line_item_id = fake_stripe_id("il", "new line item")
    data["lines"]["data"][0] = {
        "id": new_line_item_id,
        "object": "line_item",
        "type": "subscription",
        "created": unix_timestamp(datetime(2021, 10, 28, tzinfo=timezone.utc)),
        "subscription": data["lines"]["data"][0]["subscription"],
        "subscription_item": data["lines"]["data"][0]["subscription_item"],
        "price": raw_stripe_price_data,
        "amount": 500,
        "currency": "usd",
    }
    invoice, actions = ingest_stripe_invoice(dbsession, data)
    dbsession.commit()
    assert len(invoice.line_items) == 1
    assert invoice.line_items[0].stripe_id == new_line_item_id
    assert actions == {
        "created": {
            f"line_item:{new_line_item_id}",
        },
        "no_change": {
            f"invoice:{data['id']}",
            f"price:{data['lines']['data'][0]['price']['id']}",
        },
        "deleted": {
            f"line_item:{old_line_item_id}",
        },
    }


def test_ingest_sample_data(dbsession, stripe_test_json):
    """Stripe sample JSON can be ingested."""
    obj, actions = ingest_stripe_object(dbsession, stripe_test_json)
    assert obj is not None
    assert type(obj.get_email_id()) in (type(None), UUID)
    assert actions


def test_parse_sample_data_acoustic(dbsession, stripe_test_json):
    """Stripe sample JSON can be ingested."""
    obj, actions = ingest_stripe_object(dbsession, stripe_test_json)
    assert obj is not None
    assert type(obj.get_email_id()) in (type(None), UUID)
    assert actions
    dbsession.commit()
    with pytest.raises(StripeToAcousticParseError):
        add_stripe_object_to_acoustic_queue(dbsession, stripe_test_json)


def test_get_email_id_customer(
    dbsession, stripe_customer_data, contact_with_stripe_customer
):
    """A Stripe Customer can return the related email_id.
    `stripe_customer_data` is used when building `contact_with_stripe_customer`
    """

    customer = get_stripe_customer_by_stripe_id(
        dbsession, stripe_customer_data["stripe_id"]
    )

    assert customer.get_email_id() == contact_with_stripe_customer.email.email_id


def test_get_email_id_subscription(
    dbsession,
    contact_with_stripe_subscription,
    stripe_customer_data,
    stripe_price_data,
    stripe_subscription_data,
    stripe_subscription_item_data,
):
    """A Stripe Subscription and related objects can return the related email_id.
    The `stripe_` fixtures that are included here are used to build the data
    associated with `contact_with_stripe_subscription`
    """
    customer = get_stripe_customer_by_stripe_id(
        dbsession, stripe_customer_data["stripe_id"]
    )
    subscription = get_stripe_subscription_by_stripe_id(
        dbsession, stripe_subscription_data["stripe_id"]
    )
    subscription_item = get_stripe_subscription_item_by_stripe_id(
        dbsession, stripe_subscription_item_data["stripe_id"]
    )
    price = get_stripe_price_by_stripe_id(dbsession, stripe_price_data["stripe_id"])

    email_id = contact_with_stripe_subscription.email.email_id
    assert customer.get_email_id() == email_id
    assert subscription.get_email_id() == email_id
    assert subscription_item.get_email_id() == email_id
    # Prices always return None since they can relate to multiple contacts.
    assert price.get_email_id() is None


def test_get_email_id_invoice(
    dbsession, contact_with_stripe_customer, raw_stripe_invoice_data
):
    """A Stripe Invoice and related objects can return the related email_id."""
    invoice, actions = ingest_stripe_invoice(dbsession, raw_stripe_invoice_data)
    dbsession.commit()
    assert actions
    customer = get_stripe_customer_by_stripe_id(
        dbsession, raw_stripe_invoice_data["customer"]
    )
    invoice = get_stripe_invoice_by_stripe_id(dbsession, raw_stripe_invoice_data["id"])
    line_item = get_stripe_invoice_line_item_by_stripe_id(
        dbsession, raw_stripe_invoice_data["lines"]["data"][0]["id"]
    )
    price = get_stripe_price_by_stripe_id(
        dbsession, raw_stripe_invoice_data["lines"]["data"][0]["price"]["id"]
    )

    email_id = contact_with_stripe_customer.email.email_id
    assert customer.get_email_id() == email_id
    assert invoice.get_email_id() == email_id
    assert line_item.get_email_id() == email_id
    # Prices always return None since they can relate to multiple contacts.
    assert price.get_email_id() is None


def test_ingest_unknown_stripe_object_raises(dbsession):
    """Ingesting an unknown type of Stripe object raises an exception."""
    re_id = fake_stripe_id("re", "refund")
    data = {"id": re_id, "object": "refund"}
    with pytest.raises(StripeIngestUnknownObjectError) as excinfo:
        ingest_stripe_object(dbsession, data)
    exception = excinfo.value
    assert str(exception) == f"Unknown Stripe object 'refund' with ID {re_id!r}."
    assert repr(exception) == f"StripeIngestUnknownObjectError('refund', {re_id!r})"


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
