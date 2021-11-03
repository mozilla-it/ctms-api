"""Unit tests for POST /stripe (add or update Stripe objects)"""

from tests.unit.test_ingest_stripe import stripe_customer_data


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
