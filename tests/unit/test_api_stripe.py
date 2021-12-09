"""Unit tests for POST /stripe (add or update Stripe objects)"""

import json
from base64 import b64encode
from datetime import datetime, timezone
from unittest import mock

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError
from structlog.testing import capture_logs

from ctms.app import app, get_pubsub_claim
from ctms.models import PendingAcousticRecord
from tests.unit.test_ingest_stripe import (
    stripe_customer_data,
    stripe_invoice_data,
    stripe_subscription_data,
)


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


def test_api_post_stripe_customer(client, dbsession, example_contact):
    """Stripe customer data can be imported."""
    data = stripe_customer_data()
    resp = client.post("/stripe", json=data)
    assert resp.status_code == 200
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par.email.stripe_customer.stripe_id == data["id"]


def test_api_post_stripe_customer_without_contact(client, dbsession):
    """Stripe customer data without a related contact can be imported."""
    data = stripe_customer_data()
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


def test_api_post_stripe_customer_missing_data(client, dbsession):
    """Missing data from customer data is a 400 error."""
    data = stripe_customer_data()
    del data["description"]  # The FxA ID
    resp = client.post("/stripe", json=data)
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Unable to process Stripe object."}


def test_api_post_sample_data(dbsession, client, stripe_test_json):
    """Stripe sample data can be POSTed directly."""
    resp = client.post("/stripe", json=stripe_test_json)
    assert resp.status_code == 200


def test_api_post_stripe_trace_customer(client, dbsession, example_contact):
    """Stripe customer data can be traced via email."""
    data = stripe_customer_data()
    email = data["email"] = "customer+trace-me-mozilla-123@example.com"
    with capture_logs() as caplog:
        resp = client.post("/stripe", json=data)
    assert resp.status_code == 200
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par.email.stripe_customer.stripe_id == data["id"]
    assert len(caplog) == 1
    assert caplog[0]["trace"] == email
    assert caplog[0]["trace_json"] == data


def test_api_post_stripe_from_pubsub_customer(
    dbsession, pubsub_client, example_contact
):
    """Stripe customer data as a PubSub push can be imported."""
    data = stripe_customer_data()
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par.email.stripe_customer.stripe_id == data["id"]


def test_api_post_stripe_from_pubsub_without_contact(pubsub_client, dbsession):
    """Stripe customer data without a related contact can be imported from pubsub."""
    data = stripe_customer_data()
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}
    par = dbsession.query(PendingAcousticRecord).one_or_none()
    assert par is None


def test_api_post_stripe_from_pubsub_item_dict(
    dbsession, pubsub_client, example_contact
):
    """A PubSub push of multiple items, keyed by table:id, can be imported."""
    customer_data = stripe_customer_data()
    subscription_data = stripe_subscription_data()
    invoice_data = stripe_invoice_data()
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


def test_api_post_stripe_from_pubsub_customer_missing_data(dbsession, pubsub_client):
    """Missing data from PubSub push is a 202, so it doesn't resend."""
    data = stripe_customer_data()
    del data["description"]  # The FxA ID
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 202  # Accepted
    assert resp.json() == {
        "status": "Accepted but not processed",
        "message": "Errors processing the data, do not send again.",
    }
    assert dbsession.query(PendingAcousticRecord).one_or_none() is None


def test_api_post_stripe_from_pubsub_bad_data(dbsession, pubsub_client):
    """Bad data from PubSub push is a 202, so it doesn't resend."""
    data = stripe_customer_data()
    resp = pubsub_client.post("/stripe_from_pubsub", json=data)
    assert resp.status_code == 202  # Accepted
    assert resp.json() == {
        "status": "Accepted but not processed",
        "message": "Message does not appear to be from pubsub, do not send again.",
    }


def test_api_post_stripe_from_pubsub_list(dbsession, pubsub_client):
    """A list from a PubSub push is a 202, accepted but not processed."""
    customer_data = stripe_customer_data()
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap([customer_data]))
    assert resp.status_code == 202
    assert resp.json() == {
        "status": "Accepted but not processed",
        "message": "Unknown payload type, do not send again.",
    }


def test_api_post_pubsub_sample_data(dbsession, pubsub_client, stripe_test_json):
    """Stripe sample data can be POSTed from PubSub."""
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(stripe_test_json))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}


def test_api_post_pubsub_unknown_stripe_object(dbsession, pubsub_client):
    """An unknown Stripe object is silently ignored."""
    data = {"object": "payment_method", "id": "pm_ABC123"}
    with capture_logs() as cap_logs:
        resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 0}
    assert len(cap_logs) == 1
    assert cap_logs[0]["stripe_unknown_objects"] == ["payment_method"]


def test_api_post_pubsub_trace_customer(dbsession, pubsub_client):
    """Stripe customer data from PubSub can be traced via email."""
    data = stripe_customer_data()
    email = data["email"] = "customer+trace-me-mozilla-123@example.com"
    with capture_logs() as caplog:
        resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 200
    assert resp.json() == {"status": "OK", "count": 1}
    assert len(caplog) == 1
    assert caplog[0]["trace"] == email
    assert caplog[0]["trace_json"] == data


def test_api_post_pubsub_integrity_error_is_409(dbsession, pubsub_client):
    """An integrity error is turned into a 409 Conflict"""
    data = stripe_customer_data()
    err = IntegrityError(
        "INSERT INTO...", {"stripe_id": data["id"]}, "Duplicate key value"
    )
    with capture_logs() as caplog, mock.patch(
        "ctms.ingest_stripe.create_stripe_customer", side_effect=err
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


def test_api_post_pubsub_deadlock_is_409(dbsession, pubsub_client):
    """A deadlock is turned into a 409 Conflict"""
    data = stripe_customer_data()
    err = OperationalError("INSERT INTO...", {"stripe_id": data["id"]}, "Deadlock")
    with capture_logs() as caplog, mock.patch(
        "ctms.ingest_stripe.create_stripe_customer", side_effect=err
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
