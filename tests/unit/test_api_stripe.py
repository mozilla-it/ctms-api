"""Unit tests for POST /stripe (add or update Stripe objects)"""

import json
from base64 import b64encode
from datetime import datetime, timezone

import pytest

from ctms.app import app, get_pubsub_claim
from tests.unit.test_ingest_stripe import stripe_customer_data


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


def test_api_post_stripe_customer(client, dbsession):
    """Stripe customer data can be imported."""
    resp = client.post("/stripe", json=stripe_customer_data())
    assert resp.status_code == 200


def test_api_post_stripe_customer_bad_data(client, dbsession):
    """Data that does not look like a Stripe object is a 400 error."""
    data = {"email": "fake@example.com"}
    resp = client.post("/stripe", json=data)
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Request JSON is not recognized."}


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


def test_api_post_stripe_from_pubsub_customer(dbsession, pubsub_client):
    """Stripe customer data as a PubSub push can be imported."""
    resp = pubsub_client.post(
        "/stripe_from_pubsub", json=pubsub_wrap(stripe_customer_data())
    )
    assert resp.status_code == 200


def test_api_post_stripe_from_pubsub_customer_missing_data(dbsession, pubsub_client):
    """Missing data from PubSub push is a 202, so it doesn't resend."""
    data = stripe_customer_data()
    del data["description"]  # The FxA ID
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(data))
    assert resp.status_code == 202  # Accepted


def test_api_post_stripe_from_pubsub_bad_data(dbsession, pubsub_client):
    """Bad data from PubSub push is a 202, so it doesn't resend."""
    data = stripe_customer_data()
    resp = pubsub_client.post("/stripe_from_pubsub", json=data)
    assert resp.status_code == 202  # Accepted


def test_api_post_pubsub_sample_data(dbsession, pubsub_client, stripe_test_json):
    """Stripe sample data can be POSTed from PubSub."""
    resp = pubsub_client.post("/stripe_from_pubsub", json=pubsub_wrap(stripe_test_json))
    assert resp.status_code == 200