"""Unit tests for GET /ctms/{email_id}"""

import pytest


def test_get_ctms_for_mostly_empty(client, email_factory):
    """GET /ctms/{email_id} returns a contact with most fields unset."""
    contact = email_factory(newsletters=1)
    newsletter = contact.newsletters[0]

    email_id = str(contact.email_id)
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
            "basket_token": str(contact.basket_token),
            "create_timestamp": contact.create_timestamp.isoformat(),
            "double_opt_in": contact.double_opt_in,
            "email_format": contact.email_format,
            "email_id": str(contact.email_id),
            "email_lang": contact.email_lang,
            "first_name": contact.first_name,
            "has_opted_out_of_email": contact.has_opted_out_of_email,
            "last_name": contact.last_name,
            "mailing_country": contact.mailing_country,
            "primary_email": contact.primary_email,
            "sfdc_id": None,
            "unsubscribe_reason": contact.unsubscribe_reason,
            "update_timestamp": contact.update_timestamp.isoformat(),
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
                "format": newsletter.format,
                "lang": newsletter.lang,
                "name": newsletter.name,
                "source": newsletter.source,
                "subscribed": newsletter.subscribed,
                "unsub_reason": newsletter.unsub_reason,
                "create_timestamp": newsletter.create_timestamp.isoformat(),
                "update_timestamp": newsletter.update_timestamp.isoformat(),
            }
        ],
        "status": "ok",
        "vpn_waitlist": {"geo": None, "platform": None},
        "relay_waitlist": {"geo": None},
        "waitlists": [],
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
                "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
            },
            {
                "format": "H",
                "lang": "en",
                "name": "mozilla-welcome",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
                "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
            },
        ],
        "status": "ok",
        "vpn_waitlist": {"geo": "fr", "platform": "ios,mac"},
        "relay_waitlist": {"geo": "fr"},
        "waitlists": [
            {
                "fields": {"geo": "fr", "platform": "win64"},
                "name": "example-product",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
                "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
            },
            {
                "fields": {"geo": "fr"},
                "name": "relay",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
                "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
            },
            {
                "fields": {"geo": "fr", "platform": "ios,mac"},
                "name": "vpn",
                "source": None,
                "subscribed": True,
                "unsub_reason": None,
                "create_timestamp": "2020-12-05T19:21:50.908000+00:00",
                "update_timestamp": "2021-02-04T15:36:57.511000+00:00",
            },
        ],
    }


def test_get_ctms_not_found(client, dbsession):
    """GET /ctms/{unknown email_id} returns a 404."""
    email_id = "cad092ec-a71a-4df5-aa92-517959caeecb"
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Unknown email_id"}


@pytest.mark.parametrize("waitlist_name", ["vpn", "relay"])
def test_get_ctms_without_geo_in_waitlist(
    waitlist_name, client, dbsession, waitlist_factory
):
    existing_waitlist = waitlist_factory(name=waitlist_name, fields={})
    dbsession.flush()
    email_id = existing_waitlist.email.email_id

    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 200
