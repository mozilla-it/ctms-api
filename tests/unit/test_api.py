"""pytest tests for API functionality"""
from uuid import UUID

from ctms.crud import (
    create_amo,
    create_email,
    create_fxa,
    create_newsletter,
    create_vpn_waitlist,
)
from ctms.models import Email
from ctms.sample_data import SAMPLE_CONTACTS


def test_api_example(dbsession, client):
    """Test that the API examples are valid."""
    example = SAMPLE_CONTACTS[UUID("332de237-cab7-4461-bcc3-48e68f42bd5c")]
    create_email(dbsession, example.email)
    create_amo(dbsession, example.amo)
    create_fxa(dbsession, example.fxa)
    create_vpn_waitlist(dbsession, example.vpn_waitlist)
    for newsletter in example.newsletters:
        create_newsletter(dbsession, newsletter)

    resp = client.get("/ctms/332de237-cab7-4461-bcc3-48e68f42bd5c")
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


def test_empty_db(dbsession):
    """Database is empty at the start of tests."""
    assert dbsession.query(Email).count() == 0
