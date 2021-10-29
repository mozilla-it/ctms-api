"""Test ingesting of Stripe data"""

from __future__ import annotations

import json
import os.path
from base64 import b64encode
from datetime import datetime, timezone
from time import mktime
from typing import Dict, Optional
from uuid import uuid4

import pytest

from ctms.crud import create_email, create_stripe_customer, get_contact_by_email_id
from ctms.ingest_stripe import (
    StripeIngestBadObjectError,
    StripeIngestUnknownObjectError,
    ingest_stripe_customer,
    ingest_stripe_object,
)
from ctms.schemas import EmailInSchema, StripeCustomerCreateSchema


def fake_stripe_id(prefix: str, seed: str, suffix: Optional[str] = None) -> str:
    """Create a fake Stripe ID for testing"""
    body = b64encode(seed.encode()).decode().replace("=", "")
    return f"{prefix}_{body}{suffix if suffix else ''}"


# Documentation and test Stripe IDs
FAKE_CUSTOMER_ID = fake_stripe_id("cus", "customer")
FAKE_PAYMENT_METHOD_ID = fake_stripe_id("pm", "payment_method")


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


def test_ids():
    """Get the fake IDs, to make it easier to copy to schemas."""
    assert FAKE_CUSTOMER_ID == "cus_Y3VzdG9tZXI"
    assert FAKE_PAYMENT_METHOD_ID == "pm_cGF5bWVudF9tZXRob2Q"


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


@pytest.mark.parametrize("filename", ("customer_01.json",))
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
