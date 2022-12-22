"""Unit tests for GET /ctms/{email_id}"""
from uuid import uuid4

from structlog.testing import capture_logs

from ctms.models import Email


def test_get_ctms_for_minimal_contact(client, minimal_contact):
    """GET /ctms/{email_id} returns a contact with most fields unset."""
    email_id = minimal_contact.email.email_id
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
    assert resp.json() == {
        "amo": {
            "add_on_ids": None,
            "create_timestamp": None,
            "display_name": None,
            "email_opt_in": False,
            "language": None,
            "last_login": None,
            "location": None,
            "profile_url": None,
            "update_timestamp": None,
            "user": False,
            "user_id": None,
            "username": None,
        },
        "email": {
            "basket_token": "142e20b6-1ef5-43d8-b5f4-597430e956d7",
            "create_timestamp": "2014-01-22T15:24:00+00:00",
            "double_opt_in": False,
            "email_format": "H",
            "email_id": "93db83d4-4119-4e0c-af87-a713786fa81d",
            "email_lang": "en",
            "first_name": None,
            "has_opted_out_of_email": False,
            "last_name": None,
            "mailing_country": "us",
            "primary_email": "ctms-user@example.com",
            "sfdc_id": "001A000001aABcDEFG",
            "unsubscribe_reason": None,
            "update_timestamp": "2020-01-22T15:24:00+00:00",
        },
        "fxa": {
            "created_date": None,
            "account_deleted": False,
            "first_service": None,
            "fxa_id": None,
            "lang": None,
            "primary_email": None,
        },
        "mofo": {
            "mofo_contact_id": None,
            "mofo_email_id": None,
            "mofo_relevant": False,
        },
        "newsletters": [
            {
                "format": "H",
                "lang": "en",
                "name": "app-dev",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "maker-party",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-foundation",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-learning-network",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
        ],
        "status": "ok",
        "vpn_waitlist": {"geo": None, "platform": None},
        "relay_waitlist": {"geo": None},
        "waitlists": [],
    }


def test_get_ctms_for_maximal_contact(client, maximal_contact):
    """GET /ctms/{email_id} returns a contact with almost all fields set."""
    email_id = maximal_contact.email.email_id
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
    assert resp.json() == {
        "amo": {
            "add_on_ids": "fanfox,foxfan",
            "create_timestamp": "2017-05-12T15:16:00+00:00",
            "display_name": "#1 Mozilla Fan",
            "email_opt_in": True,
            "language": "fr,en",
            "last_login": "2020-01-27",
            "location": "The Inter",
            "profile_url": "firefox/user/14508209",
            "update_timestamp": "2020-01-27T14:25:43+00:00",
            "user": True,
            "user_id": "123",
            "username": "Mozilla1Fan",
        },
        "email": {
            "basket_token": "d9ba6182-f5dd-4728-a477-2cc11bf62b69",
            "create_timestamp": "2010-01-01T08:04:00+00:00",
            "double_opt_in": True,
            "email_format": "H",
            "email_id": "67e52c77-950f-4f28-accb-bb3ea1a2c51a",
            "email_lang": "fr",
            "first_name": "Fan",
            "has_opted_out_of_email": False,
            "last_name": "of Mozilla",
            "mailing_country": "ca",
            "primary_email": "mozilla-fan@example.com",
            "sfdc_id": "001A000001aMozFan",
            "unsubscribe_reason": "done with this mailing list",
            "update_timestamp": "2020-01-28T14:50:00+00:00",
        },
        "fxa": {
            "created_date": "2019-05-22T08:29:31.906094+00:00",
            "account_deleted": False,
            "first_service": "monitor",
            "fxa_id": "611b6788-2bba-42a6-98c9-9ce6eb9cbd34",
            "lang": "fr,fr-CA",
            "primary_email": "fxa-firefox-fan@example.com",
        },
        "mofo": {
            "mofo_contact_id": "5e499cc0-eeb5-4f0e-aae6-a101721874b8",
            "mofo_email_id": "195207d2-63f2-4c9f-b149-80e9c408477a",
            "mofo_relevant": True,
        },
        "newsletters": [
            {
                "format": "H",
                "lang": "en",
                "name": "ambassadors",
                "source": "https://www.mozilla.org/en-US/contribute/studentambassadors/",
                "subscribed": False,
                "unsub_reason": "Graduated, don't have time for FSA",
            },
            {
                "format": "T",
                "lang": "fr",
                "name": "common-voice",
                "source": "https://commonvoice.mozilla.org/fr",
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "fr",
                "name": "firefox-accounts-journey",
                "source": "https://www.mozilla.org/fr/firefox/accounts/",
                "subscribed": False,
                "unsub_reason": "done with this mailing list",
            },
            {
                "format": "H",
                "lang": "en",
                "name": "firefox-os",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "fr",
                "name": "hubs",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-festival",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
            {
                "format": "H",
                "lang": "fr",
                "name": "mozilla-foundation",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
            },
        ],
        "status": "ok",
        "vpn_waitlist": {"geo": "ca", "platform": "windows,android"},
        "relay_waitlist": {"geo": "cn"},
        "waitlists": [
            {
                "fields": {},
                "geo": "fr",
                "name": "a-software",
                "source": "https://a-software.mozilla.org/",
            },
            {
                "fields": {},
                "geo": "cn",
                "name": "relay",
                "source": None,
            },
            {
                "fields": {"platform": "win64"},
                "geo": "fr",
                "name": "super-product",
                "source": "https://super-product.mozilla.org/",
            },
            {
                "fields": {"platform": "windows,android"},
                "geo": "ca",
                "name": "vpn",
                "source": None,
            },
        ],
    }


def test_get_ctms_for_api_example(client, example_contact):
    """The API examples represent a valid contact with many fields set.
    Test that the API examples are valid."""
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
            "double_opt_in": True,
            "email_format": "H",
            "email_id": "332de237-cab7-4461-bcc3-48e68f42bd5c",
            "email_lang": "en",
            "first_name": "Jane",
            "has_opted_out_of_email": False,
            "last_name": "Doe",
            "mailing_country": "us",
            "primary_email": "contact@example.com",
            "sfdc_id": "001A000023aABcDEFG",
            "unsubscribe_reason": None,
            "update_timestamp": "2021-01-28T21:26:57.511000+00:00",
        },
        "fxa": {
            "account_deleted": False,
            "created_date": "2021-01-29T18:43:49.082375+00:00",
            "first_service": "sync",
            "fxa_id": "6eb6ed6ac3b64259968aa490c6c0b9df",
            "lang": "en,en-US",
            "primary_email": "my-fxa-acct@example.com",
        },
        "mofo": {
            "mofo_contact_id": None,
            "mofo_email_id": None,
            "mofo_relevant": False,
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
        "relay_waitlist": {"geo": "fr"},
        "waitlists": [
            {
                "fields": {"platform": "win64"},
                "geo": "fr",
                "name": "example-product",
                "source": None,
            },
            {
                "fields": {},
                "geo": "fr",
                "name": "relay",
                "source": None,
            },
            {
                "fields": {"platform": "ios,mac"},
                "geo": "fr",
                "name": "vpn",
                "source": None,
            },
        ],
    }


def test_get_ctms_not_found(client, dbsession):
    """GET /ctms/{unknown email_id} returns a 404."""
    email_id = "cad092ec-a71a-4df5-aa92-517959caeecb"
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Unknown email_id"}


def test_get_ctms_not_traced(client, example_contact):
    """Most CTMS contacts are not traced."""
    email_id = example_contact.email.email_id
    with capture_logs() as caplog:
        resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
    assert len(caplog) == 1
    assert "trace" not in caplog[0]


def test_get_ctms_with_tracing(client, dbsession):
    """The log parameter trace is set when a traced email is requested."""
    email_id = uuid4()
    email = "test+trace-me-mozilla-123@example.com"
    record = Email(
        email_id=email_id,
        primary_email=email,
        double_opt_in=False,
        email_format="T",
        has_opted_out_of_email=False,
    )
    dbsession.add(record)
    dbsession.commit()
    with capture_logs() as caplog:
        resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
    assert len(caplog) == 1
    assert caplog[0]["trace"] == email
    assert "trace_json" not in caplog[0]
