"""pytest tests for API functionality"""
from uuid import UUID

import pytest

from ctms.crud import (
    create_amo,
    create_email,
    create_fxa,
    create_newsletter,
    create_vpn_waitlist,
)
from ctms.models import Email
from ctms.sample_data import SAMPLE_CONTACTS


def test_api_example(client, example_contact):
    """Test that the API examples are valid."""
    email_id = example_contact.email.email_id
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
    assert resp.json() == {
        "amo": {
            "add_on_ids": "add-on-1,add-on-2",
            "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
            "display_name": "Add-ons Author",
            "email_opt_in": False,
            "language": "en",
            "last_login": "2021-01-28",
            "location": "California",
            "profile_url": "firefox/user/98765",
            "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
            "user": True,
            "user_id": "98765",
            "username": "AddOnAuthor",
        },
        "email": {
            "basket_token": "c4a7d759-bb52-457b-896b-90f1d3ef8433",
            "create_timestamp": "2020-03-28T15:41:00+00:00",
            "email_format": "H",
            "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
            "email_lang": "en",
            "first_name": "Jane",
            "has_opted_out_of_email": False,
            "last_name": "Doe",
            "mailing_country": "us",
            "mofo_id": None,
            "mofo_relevant": False,
            "primary_email": "contact@example.com",
            "sfdc_id": "001A000023aABcDEFG",
            "unsubscribe_reason": None,
            "update_timestamp": "2021-01-28T21:26:57.511000+00:00",
        },
        "fxa": {
            "account_deleted": False,
            "created_date": "2021-01-29T18:43:49.082375+00:00",
            "first_service": "sync",
            "fxa_id": "6eb6ed6a-c3b6-4259-968a-a490c6c0b9df",
            "lang": "en,en-US",
            "primary_email": "my-fxa-acct@example.com",
        },
        "newsletters": [
            {
                "format": "H",
                "lang": "en",
                "name": "firefox-welcome",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-welcome",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
        ],
        "status": "ok",
        "vpn_waitlist": {"geo": "fr", "platform": "ios,mac"},
    }


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
        ("mofo_id", "195207d2-63f2-4c9f-b149-80e9c408477a"),
    ],
)
def test_ctms_by_alt_id(sample_contacts, client, alt_id_name, alt_id_value):
    """The desired contact can be fetched by alternate ID."""
    maximal_id, contact = sample_contacts["maximal"]
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["email"]["email_id"] == str(maximal_id)


@pytest.mark.parametrize(
    "alt_id_name,alt_id_value",
    [
        ("email_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("primary_email", "unknown-user@example.com"),
        ("amo_user_id", 404),
        ("basket_token", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("fxa_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
        ("fxa_primary_email", "unknown-user@example.com"),
        ("sfdc_id", "001A000404aUnknown"),
        ("mofo_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
    ],
)
def test_ctms_by_alt_id_none_found(sample_contacts, client, alt_id_name, alt_id_value):
    """An empty list is returned when no contacts have the alternate ID."""
    maximal_id, contact = sample_contacts["maximal"]
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


def test_empty_db(dbsession):
    """Database is empty at the start of tests."""
    assert dbsession.query(Email).count() == 0
