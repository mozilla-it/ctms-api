"""pytest tests for API functionality"""
from typing import Callable, List
from uuid import UUID

import pytest

from ctms.crud import get_contacts_by_any_id
from ctms.models import Email
from ctms.sample_data import SAMPLE_CONTACTS
from ctms.schemas import ContactSchema


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
            "mofo_id": None,
            "mofo_relevant": False,
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
            "mofo_id": "195207d2-63f2-4c9f-b149-80e9c408477a",
            "mofo_relevant": True,
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
    }


def test_get_ctms_for_api_example(client, example_contact):
    """The API examples represent a valid contact with many fields set."""
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
            "double_opt_in": True,
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
            "fxa_id": "6eb6ed6ac3b64259968aa490c6c0b9df",
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


def test_get_ctms_not_found(client, dbsession):
    """GET /ctms/{unknown email_id} returns a 404."""
    email_id = "cad092ec-a71a-4df5-aa92-517959caeecb"
    resp = client.get(f"/ctms/{email_id}")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Unknown email_id"}


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
def test_get_ctms_by_alt_id(sample_contacts, client, alt_id_name, alt_id_value):
    """The desired contact can be fetched by alternate ID."""
    maximal_id, contact = sample_contacts["maximal"]
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["email"]["email_id"] == str(maximal_id)


def test_get_ctms_by_no_ids_is_error(client, dbsession):
    """Calling GET /ctms with no ID query is an error."""
    resp = client.get("/ctms")
    assert resp.status_code == 400
    assert resp.json() == {
        "detail": "No identifiers provided, at least one is needed: email_id, primary_email, basket_token, sfdc_id, mofo_id, amo_user_id, fxa_id, fxa_primary_email"
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
        ("mofo_id", "cad092ec-a71a-4df5-aa92-517959caeecb"),
    ],
)
def test_get_ctms_by_alt_id_none_found(client, dbsession, alt_id_name, alt_id_value):
    """An empty list is returned when no contacts have the alternate ID."""
    resp = client.get("/ctms", params={alt_id_name: alt_id_value})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


def test_create_basic_no_id(add_contact):
    """Most straightforward contact creation succeeds."""

    def _remove_id(contact):
        contact.email.email_id = None
        return contact

    saved_contacts, sample = add_contact(modifier=_remove_id, check_redirect=False)

    assert saved_contacts[0].email.email_id != sample.email.email_id
    del saved_contacts[0].email.email_id
    del sample.email.email_id

    assert saved_contacts[0].email.equivalent(sample.email)


def test_create_basic_with_id(add_contact):
    """Most straightforward contact creation succeeds."""
    saved_contacts, sample = add_contact()
    assert saved_contacts[0].email.equivalent(sample.email)


def test_create_basic_idempotent(add_contact):
    """Creating a contact works across retries."""
    saved_contacts, sample = add_contact()
    saved_contacts, sample = add_contact()
    assert saved_contacts[0].email.equivalent(sample.email)


def test_create_basic_with_id_collision(add_contact):
    """Creating a contact with the same id but different data fails."""
    add_contact()

    def _change_mailing(contact):
        contact.email.mailing_country = "mx"
        return contact

    saved_contacts, sample = add_contact(
        modifier=_change_mailing, code=409, check_redirect=False
    )
    assert saved_contacts[0].email.mailing_country == "us"


def test_create_basic_with_basket_collision(add_contact):
    """Creating a contact with diff ids but same email fails.
    We override the basket token so that we know we're not colliding on that here.
    See other test for that check
    """
    saved_contacts, orig_sample = add_contact()
    assert saved_contacts[0].email.equivalent(orig_sample.email)

    def _change_basket(contact):
        contact.email.email_id = UUID("229cfa16-a8c9-4028-a9bd-fe746dc6bf73")
        contact.email.basket_token = UUID("df9f7086-4949-4b2d-8fcf-49167f8f783d")
        return contact

    saved_contacts, _ = add_contact(
        modifier=_change_basket, code=409, check_redirect=False
    )
    assert saved_contacts[0].email.equivalent(orig_sample.email)


def test_create_basic_with_email_collision(add_contact):
    """Creating a contact with diff ids but same basket token fails.
    We override the email so that we know we're not colliding on that here.
    See other test for that check
    """
    saved_contacts, orig_sample = add_contact()
    assert saved_contacts[0].email.equivalent(orig_sample.email)

    def _change_primary_email(contact):
        contact.email.email_id = UUID("229cfa16-a8c9-4028-a9bd-fe746dc6bf73")
        contact.email.primary_email = "foo@bar.com"
        return contact

    saved_contacts, _ = add_contact(
        modifier=_change_primary_email, code=409, check_redirect=False
    )
    assert saved_contacts[0].email.equivalent(orig_sample.email)
