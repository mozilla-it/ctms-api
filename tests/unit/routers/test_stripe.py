"""Unit tests for POST /stripe (add or update Stripe objects)"""

import json
from base64 import b64encode
from datetime import datetime, timezone
from unittest import mock

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError
from structlog.testing import capture_logs

from ctms.app import app
from ctms.models import PendingAcousticRecord
from ctms.routers.stripe import get_pubsub_claim
from tests.data import fake_stripe_id
from tests.unit.conftest import FAKE_STRIPE_CUSTOMER_ID


def pubsub_wrap(data):
    """Wrap data as a pubsub message."""
    publish_time = datetime.now(tz=timezone.utc).isoformat()
    message_id = "202111011704"
    return {
        "message": {
            "attributes": {"key": "value"},
            "data": b64encode(json.dumps(data).encode()).decode("ascii"),
            "messageId": message_id,
            "message_id": message_id,
            "publishTime": publish_time,
            "publish_time": publish_time,
        },
        "subscription": "projects/fxa/subscriptions/fxa-subscription",
    }


@pytest.fixture
def pubsub_client(anon_client):
    """
    A test client that passes PubSub authentication.

    The claim data comes from the documentation:
    https://cloud.google.com/pubsub/docs/push#jwt_format
    """

    claim = {
        "aud": "https://example.com",
        "azp": "113774264463038321964",
        "email": "gae-gcp@appspot.gserviceaccount.com",
        "sub": "113774264463038321964",
        "email_verified": True,
        "exp": 1550185935,
        "iat": 1550182335,
        "iss": "https://accounts.google.com",
    }

    app.dependency_overrides[get_pubsub_claim] = lambda: claim
    yield anon_client
    del app.dependency_overrides[get_pubsub_claim]


def test_api_post_stripe_customer(
    client, dbsession, email_factory, stripe_customer_data_factory
):
    """Stripe customer data can be imported."""
    email = email_factory(fxa=True)
    dbsession.commit()
    data = stripe_customer_data_factory(
        email=email.primary_email, fxa_id=email.fxa.fxa_id
    )
    resp = client.post("/stripe", json=data)
    assert resp.status_code == 200
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par.email.stripe_customer.stripe_id == data["id"]


def test_api_post_stripe_customer_without_contact(
    client, dbsession, stripe_customer_data_factory
):
    """Stripe customer data without a related contact can be imported."""
    data = stripe_customer_data_factory()
    resp = client.post("/stripe", json=data)
    assert resp.status_code == 200
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par is None


def test_api_post_stripe_customer_bad_data(client, dbsession):
    """Data that does not look like a Stripe object is a 400 error."""
    data = {"email": "fake@example.com"}
    resp = client.post("/stripe", json=data)
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Request JSON is not recognized."}
    assert dbsession.query(PendingAcousticRecord).one_or_none() is None


def test_api_post_stripe_customer_missing_data(client, stripe_customer_data_factory):
    """Missing data from customer data is a 400 error."""
    resp = client.post("/stripe", json=stripe_customer_data_factory(fxa_id=None))
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Unable to process Stripe object."}


def test_api_post_sample_data(client, stripe_test_json):
    """Stripe sample data can be POSTed directly."""
    resp = client.post("/stripe", json=stripe_test_json)
    assert resp.status_code == 200


def test_api_post_stripe_trace_customer(
    client, dbsession, email_factory, stripe_customer_data_factory
):
    """Stripe customer data can be traced via email."""
    email = email_factory(
        primary_email="customer+trace-me-mozilla-123@example.com", fxa=True
    )
    dbsession.commit()
    data = stripe_customer_data_factory(
        email=email.primary_email, fxa_id=email.fxa.fxa_id
    )
    with capture_logs() as caplog:
        resp = client.post("/stripe", json=data)
    assert resp.status_code == 200
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par.email.stripe_customer.stripe_id == data["id"]
    assert len(caplog) == 1
    log = caplog[0]
    assert log["trace"] == data["email"]
    assert log["trace_json"] == data
    assert log["ingest_actions"] == {"created": [f"customer:{data['id']}"]}


def test_api_post_conflicting_fxa_id(
    dbsession, client, stripe_customer_factory, stripe_customer_data_factory
):
    """An existing customer with an FxA ID conflict is deleted."""
    existing = stripe_customer_factory(stripe_id=fake_stripe_id("cus", "old"))
    old_id = existing.stripe_id
    dbsession.commit()
    new_id = fake_stripe_id("cus", "new")
    data = stripe_customer_data_factory(id=new_id, fxa_id=existing.fxa_id)
    with capture_logs() as caplog:
        resp = client.post("/stripe", json=data)
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK"}
    assert len(caplog) == 1
    log = caplog[0]
    assert log["ingest_actions"] == {
        "created": [f"customer:{new_id}"],
        "deleted": [f"customer:{old_id}"],
    }
    assert log["fxa_id_conflict"] == data["description"]


def test_api_post_deleted_new_customer(client):
    """A new customer who starts out deleted is skipped."""
    stripe_id = fake_stripe_id("cus", "new_but_deleted")
    data = {"deleted": True, "id": stripe_id, "object": "customer"}
    with capture_logs() as caplog:
        resp = client.post("/stripe", json=data)
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK"}
    assert len(caplog) == 1
    log = caplog[0]
    assert log["ingest_actions"] == {
        "skipped": [f"customer:{stripe_id}"],
    }


def test_api_post_stripe_from_pubsub_customer(
    dbsession, pubsub_client, email_factory, stripe_customer_data_factory
):
    """Stripe customer data as a PubSub push can be imported."""
    email = email_factory(fxa=True)
    dbsession.commit()
    data = stripe_customer_data_factory(
        email=email.primary_email, fxa_id=email.fxa.fxa_id
    )
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par.email.stripe_customer.stripe_id == data["id"]


def test_api_post_stripe_from_pubsub_without_contact(
    pubsub_client, dbsession, stripe_customer_data_factory
):
    """Stripe customer data without a related contact can be imported from pubsub."""
    data = stripe_customer_data_factory()
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par is None


def test_api_post_stripe_from_pubsub_item_dict(
    dbsession,
    pubsub_client,
    example_contact,
    stripe_customer_data_factory,
    raw_stripe_subscription_data,
    raw_stripe_invoice_data,
):
    """A PubSub push of multiple items, keyed by table:id, can be imported."""
    customer_data = stripe_customer_data_factory(
        id=FAKE_STRIPE_CUSTOMER_ID, fxa_id=example_contact.fxa.fxa_id
    )
    subscription_data = raw_stripe_subscription_data
    invoice_data = raw_stripe_invoice_data
    item_dict = {
        f"from_customer_table:{customer_data['description']}": customer_data,
        f"from_subscription_table:{subscription_data['id']}": subscription_data,
        f"from_invoice_table:{invoice_data['id']}": invoice_data,
    }
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(item_dict))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 3}
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par.email.stripe_customer.stripe_id == customer_data["id"]


def test_api_post_stripe_from_pubsub_none_without_exceptions(pubsub_client):
    """A PubSub push of multiple items, keyed by table:id with no value associated."""
    item_dict = {
        "from_customer_table:stripe_id": None,
        "from_subscription_table:subscription_id": None,
        "from_invoice_table:invoice_id": None,
    }
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(item_dict))

    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 0}


def test_api_post_stripe_from_pubsub_customer_missing_data(
    dbsession, pubsub_client, stripe_customer_data_factory
):
    """Missing data from PubSub push is a 202, so it doesn't resend."""
    data = stripe_customer_data_factory(fxa_id=None)
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 202  # Accepted
    assert resp.json() == {
        "status": "Accepted but not processed",
        "message": "Errors processing the data, do not send again.",
    }
    assert dbsession.query(PendingAcousticRecord).one_or_none() is None


def test_api_post_stripe_from_pubsub_bad_data(pubsub_client):
    """Bad data from PubSub push is a 202, so it doesn't resend."""
    resp = pubsub_client.post("/stripe_from_pubsub", json={"foo": "bar"})
    assert resp.status_code == 202  # Accepted
    assert resp.json() == {
        "status": "Accepted but not processed",
        "message": "Message does not appear to be from pubsub, do not send again.",
    }


def test_api_post_stripe_from_pubsub_list(pubsub_client, stripe_customer_data_factory):
    """A list from a PubSub push is a 202, accepted but not processed."""
    data = stripe_customer_data_factory()
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap([data]))
    assert resp.status_code == 202
    assert resp.json() == {
        "status": "Accepted but not processed",
        "message": "Unknown payload type, do not send again.",
    }


def test_api_post_pubsub_sample_data(pubsub_client, stripe_test_json):
    """Stripe sample data can be POSTed from PubSub."""
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(stripe_test_json))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}


def test_api_post_pubsub_unknown_stripe_object(pubsub_client):
    """An unknown Stripe object is silently ignored."""
    data = {"object": "payment_method", "id": "pm_ABC123"}
    with capture_logs() as cap_logs:
        resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 0}
    assert len(cap_logs) == 1
    assert cap_logs[0]["ingest_actions"] == {"skipped": ["payment_method:pm_ABC123"]}


def test_api_post_pubsub_trace_customer(
    dbsession, pubsub_client, email_factory, stripe_customer_data_factory
):
    """Stripe customer data from PubSub can be traced via email."""
    email = email_factory(
        primary_email="customer+trace-me-mozilla-123@example.com", fxa=True
    )
    dbsession.commit()

    data = stripe_customer_data_factory(
        email=email.primary_email, fxa_id=email.fxa.fxa_id
    )
    with capture_logs() as caplog:
        resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))

    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}
    assert len(caplog) == 1
    assert caplog[0]["trace"] == email.primary_email
    assert caplog[0]["trace_json"] == data
    assert caplog[0]["ingest_actions"] == {"created": [f"customer:{data['id']}"]}


def test_api_post_pubsub_integrity_error_is_409(
    dbsession, pubsub_client, stripe_customer_data_factory
):
    """An integrity error is turned into a 409 Conflict"""
    data = stripe_customer_data_factory()
    err = IntegrityError(
        "INSERT INTO...", {"stripe_id": data["id"]}, "Duplicate key value"
    )
    with capture_logs() as caplog, mock.patch.object(
        dbsession, "commit", side_effect=err
    ):
        resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 409
    assert resp.json() == {"detail": "Write conflict, try again"}
    assert len(caplog) == 2
    assert caplog[0] == {
        "exc_info": True,
        "event": "IntegrityError converted to 409",
        "log_level": "error",
    }
    assert caplog[1]["status_code"] == 409


def test_api_post_pubsub_deadlock_is_409(
    dbsession, pubsub_client, stripe_customer_data_factory
):
    """A deadlock is turned into a 409 Conflict"""
    data = stripe_customer_data_factory()
    err = OperationalError("INSERT INTO...", {"stripe_id": data["id"]}, "Deadlock")
    with capture_logs() as caplog, mock.patch.object(
        dbsession, "commit", side_effect=err
    ):
        resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 409
    assert resp.json() == {"detail": "Deadlock or other issue, try again"}
    assert len(caplog) == 2
    assert caplog[0] == {
        "exc_info": True,
        "event": "OperationalError converted to 409",
        "log_level": "error",
    }
    assert caplog[1]["status_code"] == 409


def test_api_post_pubsub_conflicting_fxa_id(
    dbsession, pubsub_client, stripe_customer_factory, stripe_customer_data_factory
):
    """An existing customer with an FxA ID conflict is deleted."""
    existing = stripe_customer_factory(stripe_id=fake_stripe_id("cus", "old"))
    old_id = existing.stripe_id
    dbsession.commit()
    new_id = fake_stripe_id("cus", "new")
    data = stripe_customer_data_factory(id=new_id, fxa_id=existing.fxa_id)
    with capture_logs() as caplog:
        resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}
    assert len(caplog) == 1
    log = caplog[0]
    assert log["ingest_actions"] == {
        "created": [f"customer:{new_id}"],
        "deleted": [f"customer:{old_id}"],
    }
    assert log["fxa_id_conflict"] == data["description"]


def test_api_post_stripe_from_pubsub_deleted_new_customer(dbsession, pubsub_client):
    """A new customer who starts out deleted is skipped."""
    stripe_id = fake_stripe_id("cus", "new_but_deleted")
    data = {"deleted": True, "id": stripe_id, "object": "customer"}
    with capture_logs() as caplog:
        resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}
    assert len(caplog) == 1
    log = caplog[0]
    assert log["ingest_actions"] == {
        "skipped": [f"customer:{stripe_id}"],
    }
