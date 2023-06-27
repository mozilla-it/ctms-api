"""Unit tests for GET /ctms?alt_id=value, returning list of contacts"""
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from ctms.models import AmoAccount, Email, MozillaFoundationContact


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "67e52c77-950f-4f28-accb-bb3ea1a2c51a"),
        ("primary_email", "mozilla-fan@example.com"),
        ("amo_user_id", 123),
        ("basket_token", "d9ba6182-f5dd-4728-a477-2cc11bf62b69"),
        ("fxa_id", "611b6788-2bba-42a6-98c9-9ce6eb9cbd34"),
        ("fxa_primary_email", "fxa-firefox-fan@example.com"),
        ("sfdc_id", "001A000001aMozFan"),
        ("mofo_contact_id", "5e499cc0-eeb5-4f0e-aae6-a101721874b8"),
        ("mofo_email_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
    ],
)
def test_get_ctms_by_alt_id(maximal_contact, client, alt_id_name, alt_id_value):
    """The desired contact can be fetched by alternate ID."""
    email_id = maximal_contact.email.email_id
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["email"]["email_id"] == str(email_id)


def test_get_ctms_by_no_ids_is_error(client, dbsession):
    """Calling GET /ctms with no ID query is an error."""
    resp = client.get("/ctms")
    assert resp.status_code == 400
    assert resp.json() == {
        "detail": (
            "No identifiers provided, at least one is needed: "
            "email_id, "
            "primary_email, "
            "basket_token, "
            "sfdc_id, "
            "mofo_contact_id, "
            "mofo_email_id, "
            "amo_user_id, "
            "fxa_id, "
            "fxa_primary_email"
        )
    }


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("primary_email", "unknown-user@example.com"),
        ("amo_user_id", 404),
        ("basket_token", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("fxa_id", "cad092eca71a-4df5-aa92-517959caeecb"),
        ("fxa_primary_email", "unknown-user@example.com"),
        ("sfdc_id", "001A000404aUnknown"),
        ("mofo_contact_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("mofo_email_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
    ],
)
def test_get_ctms_by_alt_id_none_found(client, dbsession, alt_id_name, alt_id_value):
    """An empty list is returned when no contacts have the alternate ID."""
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


def test_get_not_traced(client, example_contact):
    """Most CTMS contacts are not traced."""
    params = {"primary_email": example_contact.email.primary_email}
    with capture_logs() as caplog:
        resp = client.get("/ctms", params=params)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert len(caplog) == 1
    assert "trace" not in caplog[0]


def test_get_with_tracing(client, dbsession, maximal_contact):
    """The log parameter trace is set when a traced email is requested."""
    email_id = uuid4()
    mofo_contact_id = maximal_contact.mofo.mofo_contact_id
    email = "test+trace-me-mozilla-123@example.com"
    record = Email(
        email_id=email_id,
        primary_email=email,
        double_opt_in=False,
        email_format="T",
        has_opted_out_of_email=False,
    )
    mofo = MozillaFoundationContact(
        email_id=email_id,
        mofo_relevant=True,
        mofo_contact_id=mofo_contact_id,
        mofo_email_id=uuid4(),
    )
    dbsession.add(record)
    dbsession.add(mofo)
    dbsession.commit()
    with capture_logs() as caplog:
        resp = client.get("/ctms", params={"mofo_contact_id": str(mofo_contact_id)})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert len(caplog) == 1
    assert caplog[0]["trace"] == email
    assert "trace_json" not in caplog[0]


def test_get_multiple_with_tracing(client, dbsession):
    """Multiple traced emails are comma-joined."""
    email_id1 = uuid4()
    email1 = "test+trace-me-mozilla-1@example.com"
    dbsession.add(
        Email(
            email_id=email_id1,
            primary_email=email1,
            double_opt_in=False,
            email_format="T",
            has_opted_out_of_email=False,
        )
    )
    dbsession.add(
        AmoAccount(email_id=email_id1, user_id="amo123", email_opt_in=False, user=True)
    )
    email_id2 = uuid4()
    email2 = "test+trace-me-mozilla-2@example.com"
    dbsession.add(
        Email(
            email_id=email_id2,
            primary_email=email2,
            double_opt_in=False,
            email_format="T",
            has_opted_out_of_email=False,
        )
    )
    dbsession.add(
        AmoAccount(email_id=email_id2, user_id="amo123", email_opt_in=True, user=True)
    )
    dbsession.commit()
    with capture_logs() as caplog:
        resp = client.get("/ctms", params={"amo_user_id": "amo123"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert len(caplog) == 1
    assert caplog[0]["trace"] == f"{email1},{email2}"
    assert "trace_json" not in caplog[0]
